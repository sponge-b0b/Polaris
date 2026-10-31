"""Investment Intelligence owner cause and exact Evidence-basis outcomes."""

import asyncio
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from polaris.application.evidence.current_basis import (
    BasisGuardBreak,
    BasisGuardRole,
    BasisOwnerMeaningChange,
    BasisPositiveChange,
    BasisPositiveRole,
    CurrentEvidenceBasis,
    CurrentEvidenceBasisQuery,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
)

# duplicate-code: Each owner proof imports the same inward Evidence contracts;
# sharing a test module would couple Intelligence and Portfolio falsifiers.
# jscpd:ignore-start
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentResolver,
)
from polaris.application.evidence.owner_meaning import (
    ClaimMembershipMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from polaris.application.evidence.reconstruction import (
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from polaris.application.evidence.requirements import ResolvedEvidenceRequirementVersion

# jscpd:ignore-end
from polaris.application.evidence.revalidation import (
    AtomicCurrentBasisRead,
    CurrentEvidenceBasisRevalidator,
)
from polaris.application.intelligence_judgment_history import (
    IntelligenceJudgmentClaimResolver,
    IntelligenceJudgmentMeaningReader,
    IntelligenceJudgmentTargetReader,
    IntelligenceSelectionGuard,
)
from polaris.domain.actors import ActorId, KnownActorAttribution
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import ClaimId, ClaimSpecificEvidenceScope
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.intelligence_judgment_history import (
    IntelligenceClaim,
    IntelligenceClaimCatalog,
    IntelligenceJudgmentAct,
    IntelligenceJudgmentHistory,
    IntelligenceJudgmentLane,
    IntelligenceJudgmentRoot,
    PendingDisposition,
    PendingResolution,
)
from polaris.domain.investment_intelligence import InvestmentHypothesis
from tests.application.evidence.test_current_basis import _query
from tests.domain.configuration.configuration_support import (
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.domain.test_intelligence_judgment_history import (
    K0,
    K1,
    K2,
    T3,
    _future,
    _immediate,
    _initial,
)


# duplicate-code: This store models Intelligence owner history; sharing the
# Portfolio fake would couple independent owner failure proofs.
# arid: disable
class _Store:
    def __init__(self, history: IntelligenceJudgmentHistory) -> None:
        self.history = history
        self.invalid = False

    async def load(
        self, root: IntelligenceJudgmentRoot
    ) -> IntelligenceJudgmentHistory | None:
        if self.invalid:
            raise ValueError("invalid Intelligence owner history")
        return self.history if self.history.acts[0].root == root else None


# arid: enable


# duplicate-code: An atomic read must be created from this owner's query;
# extracting a cross-owner test fixture would hide which owner is exercised.
# arid: disable
class _Participation:
    def __init__(
        self, query: CurrentEvidenceBasisQuery, key: BasisScopeKey, at: datetime
    ) -> None:
        self.query = query
        self.key = key
        self.at = at

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead:
        assert key == self.key
        return AtomicCurrentBasisRead(key, self.at, self.query)


# arid: enable


def _current_query(
    store: _Store,
) -> tuple[CurrentEvidenceBasisQuery, BasisScopeKey]:
    root = store.history.acts[0].root
    catalog = store.history.acts[0].catalog
    assert catalog is not None
    claim_id = catalog.claims[0].claim_id
    applicability = replace(
        requirement_key(), target=root, scope=ClaimSpecificEvidenceScope(claim_id)
    )
    target = asyncio.run(
        IntelligenceJudgmentTargetReader(store).read_at(
            root, effective_at=K0, known_at=K0
        )
    )
    assert isinstance(target, ResolvedTargetJudgment)
    query, key, *_ = _query(
        applicability_key=applicability,
        empty=True,
        target_version=target.version,
    )
    query._targets = TargetJudgmentResolver(IntelligenceJudgmentTargetReader(store))
    query._claims = IntelligenceJudgmentClaimResolver(store)
    owner = OwnerMeaningResolver(IntelligenceJudgmentMeaningReader(store))
    query._target_meaning = owner
    query._claim_meaning = owner

    class _Requirements:
        async def resolve(self, request, *, effective_at, known_at):
            assert request == applicability and effective_at <= known_at
            return ResolvedEvidenceRequirementVersion(
                requirement_version(
                    assignment=requirement_assignment_for_key(applicability)
                )
            )

    query._requirements = _Requirements()
    return query, key


def _revalidate(
    basis: CurrentEvidenceBasis,
    query: CurrentEvidenceBasisQuery,
    key: BasisScopeKey,
    at: datetime,
) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
    return asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            basis, _Participation(query, key, at)
        )
    )


def _catalog_correction(
    history: IntelligenceJudgmentHistory,
    catalog: IntelligenceClaimCatalog,
    basis: str,
    target_statement: str | None = None,
) -> IntelligenceJudgmentAct:
    initial = history.acts[0]
    assert type(initial.assertion) is InvestmentHypothesis
    return IntelligenceJudgmentAct(
        act_id=uuid4(),
        root=initial.root,
        attribution=initial.attribution,
        basis=basis,
        effective_at=K1,
        recorded_at=K1,
        known_at=K1,
        ancestry=(initial.act_id,),
        assertion=(
            replace(initial.assertion, statement=target_statement)
            if target_statement is not None
            else None
        ),
        catalog=catalog,
        target_predecessor=initial.act_id if target_statement is not None else None,
        catalog_predecessor=initial.act_id,
        target_status=initial.target_status if target_statement is not None else None,
        compatible_opposite_acts=(initial.act_id,),
    )


def _with_observation_support(claim: IntelligenceClaim) -> IntelligenceClaimCatalog:
    changed = replace(
        claim, surviving_support=frozenset({EvidenceObservationId(uuid4())})
    )
    return IntelligenceClaimCatalog((changed,))


def _with_distinct_actor(act: IntelligenceJudgmentAct) -> IntelligenceJudgmentAct:
    assert type(act.assertion) is InvestmentHypothesis
    attribution = KnownActorAttribution(ActorId(uuid4()))
    return replace(
        act,
        attribution=attribution,
        assertion=replace(act.assertion, actor_attribution=attribution),
    )


def _initial_with_known_actor() -> IntelligenceJudgmentHistory:
    return IntelligenceJudgmentHistory.form(_with_distinct_actor(_initial().acts[0]))


def test_complete_owner_cause_tracks_pending_resolution_and_clock_activation() -> None:
    store = _Store(_initial_with_known_actor())
    initial = store.history.acts[0]
    assert initial.catalog is not None
    claim_id = initial.catalog.claims[0].claim_id
    query, key = _current_query(store)
    reader = IntelligenceJudgmentMeaningReader(store)
    target = asyncio.run(
        IntelligenceJudgmentTargetReader(store).read_at(
            key.target, effective_at=K0, known_at=K0
        )
    )
    assert isinstance(target, ResolvedTargetJudgment)
    subject = TargetJudgmentMeaning(target.version)
    prior = asyncio.run(
        reader.read_at(key, subject, effective_at=K0, known_at=K0, read_at=K0)
    )
    assert isinstance(prior, OwnerMeaningWitness)
    assert prior.cause.complete
    assert {record.fact.act_id for record in prior.cause.fact_ancestry} == {
        initial.act_id
    }
    assert tuple(record.fact.act_id for record in prior.cause.correction_ancestry) == (
        initial.act_id,
    )
    assert prior.cause.correction_ancestry == (
        OwnerHistoryRecord(initial, initial.effective_at, initial.recorded_at),
    )
    assert prior.provenance.attribution == initial.attribution
    assert prior.provenance.basis == initial.basis
    assert prior.provenance.selected_act_id == initial.act_id
    assert prior.cause.relationship_guards == (
        IntelligenceSelectionGuard(
            key,
            initial.act_id,
            initial.act_id,
            store.history.versions,
            None,
            None,
        ),
    )

    future = _with_distinct_actor(_future(store.history))
    store.history = store.history.append(future)
    assert store.history.versions[-1] == store.history.versions[0]
    assert _revalidate(asyncio.run(query.read(key, at=K0)), query, key, K1) is None
    assert (
        asyncio.run(reader.verify_cause(prior, validation_at=K1))
        is OwnerCauseVerdict.VALID
    )

    immediate = _with_distinct_actor(
        _immediate(store.history, PendingDisposition.RETAIN)
    )
    store.history = store.history.append(immediate)
    assert len({initial.attribution, future.attribution, immediate.attribution}) == 3
    assert store.history.versions[-1][0].value == 2
    assert store.history.versions[-1][1].value == 1
    interim_basis = asyncio.run(query.read(key, at=K2))
    assert isinstance(interim_basis, CurrentEvidenceBasis)
    activated = asyncio.run(
        reader.read_at(key, subject, effective_at=T3, known_at=K2, read_at=T3)
    )
    assert isinstance(activated, OwnerMeaningWitness)
    assert activated.key == key
    assert (activated.effective_at, activated.known_at, activated.read_at) == (
        T3,
        K2,
        T3,
    )
    assert activated.meaning[0] == future.assertion
    assert activated.provenance.attribution == future.attribution
    assert activated.provenance.basis == future.basis
    assert activated.provenance.selected_act_id == future.act_id
    assert activated.cause.complete
    assert tuple(record.fact.act_id for record in activated.cause.fact_ancestry) == (
        future.act_id,
        initial.act_id,
    )
    assert tuple(
        record.fact.act_id for record in activated.cause.correction_ancestry
    ) == (initial.act_id, future.act_id, immediate.act_id)
    expected_history = tuple(
        OwnerHistoryRecord(act, act.effective_at, act.recorded_at)
        for act in store.history.acts
    )
    assert activated.cause.correction_ancestry == expected_history
    assert activated.cause.fact_ancestry == (expected_history[1], expected_history[0])
    guard = activated.cause.relationship_guards[0]
    # duplicate-code: Expected guards at distinct temporal cuts keep their
    # selected act IDs explicit; sharing construction would hide the switch.
    # arid: disable
    assert guard == IntelligenceSelectionGuard(
        key,
        future.act_id,
        initial.act_id,
        store.history.versions,
        None,
        None,
    )
    # arid: enable
    assert immediate.pending_resolutions == (
        PendingResolution(
            IntelligenceJudgmentLane.TARGET,
            future.act_id,
            PendingDisposition.RETAIN,
        ),
    )
    assert immediate.target_interim_until == T3
    assert (
        asyncio.run(reader.verify_cause(activated, validation_at=T3))
        is OwnerCauseVerdict.VALID
    )
    tampered = replace(
        activated,
        cause=replace(
            activated.cause,
            relationship_guards=(replace(guard, target_act_id=uuid4()),),
        ),
    )
    assert (
        asyncio.run(reader.verify_cause(tampered, validation_at=T3))
        is OwnerMeaningNoBasisReason.INVALID_HISTORY
    )
    clock_stale = _revalidate(interim_basis, query, key, T3)
    assert isinstance(clock_stale, StaleEvidenceBasis)
    assert clock_stale.categories == {StaleEvidenceBasisCategory.TARGET_CHANGED}
    assert clock_stale.changed_positive_references == ()
    assert {change.role for change in clock_stale.changed_owner_meanings} == {
        BasisPositiveRole.TARGET
    }
    clock_basis = asyncio.run(query.read(key, at=T3))
    assert isinstance(clock_basis, CurrentEvidenceBasis)
    assert clock_stale.changed_owner_meanings == (
        BasisOwnerMeaningChange(
            BasisPositiveRole.TARGET,
            interim_basis.owner_meaning.target,
            clock_basis.owner_meaning.target,
        ),
    )
    claim_key = replace(key, scope=ClaimSpecificEvidenceScope(claim_id))
    claim_witness = asyncio.run(
        reader.read_at(
            claim_key,
            ClaimMembershipMeaning(key.target, claim_id, store.history.versions[-1][1]),
            effective_at=T3,
            known_at=K2,
            read_at=T3,
        )
    )
    assert isinstance(claim_witness, OwnerMeaningWitness)
    assert claim_witness.provenance.attribution == initial.attribution
    assert claim_witness.provenance.basis == initial.basis
    assert claim_witness.provenance.selected_act_id == initial.act_id
    assert claim_witness.cause.relationship_guards == (
        IntelligenceSelectionGuard(
            claim_key,
            future.act_id,
            initial.act_id,
            store.history.versions,
            claim_id,
            True,
        ),
    )
    assert (
        asyncio.run(reader.verify_cause(claim_witness, validation_at=T3))
        is OwnerCauseVerdict.VALID
    )
    absent_id = ClaimId(uuid4())
    absent_key = replace(key, scope=ClaimSpecificEvidenceScope(absent_id))
    absent = asyncio.run(
        reader.read_at(
            absent_key,
            ClaimMembershipMeaning(
                key.target, absent_id, store.history.versions[-1][1]
            ),
            effective_at=T3,
            known_at=K2,
            read_at=T3,
        )
    )
    assert isinstance(absent, OwnerMeaningWitness)
    assert absent.key == absent_key
    assert (absent.effective_at, absent.known_at, absent.read_at) == (T3, K2, T3)
    assert absent.meaning == (None, store.history.versions[-1][1])
    assert absent.provenance.attribution == initial.attribution
    assert absent.provenance.basis == initial.basis
    assert absent.provenance.selected_act_id == initial.act_id
    assert absent.cause.complete
    assert absent.cause.fact_ancestry == (expected_history[1], expected_history[0])
    assert absent.cause.correction_ancestry == expected_history
    assert absent.cause.relationship_guards == (
        IntelligenceSelectionGuard(
            absent_key,
            future.act_id,
            initial.act_id,
            store.history.versions,
            absent_id,
            False,
        ),
    )


def test_target_correction_stales_exact_basis_by_target_role() -> None:
    store = _Store(_initial())
    query, key = _current_query(store)
    store.history = store.history.append(_future(store.history))
    prior = asyncio.run(query.read(key, at=K1))
    assert isinstance(prior, CurrentEvidenceBasis)
    store.history = store.history.append(
        _immediate(store.history, PendingDisposition.CANCEL)
    )
    stale = _revalidate(prior, query, key, K2)
    assert isinstance(stale, StaleEvidenceBasis)
    assert stale.categories == {StaleEvidenceBasisCategory.TARGET_CHANGED}
    assert {change.role for change in stale.changed_positive_references} == {
        BasisPositiveRole.TARGET
    }
    current = asyncio.run(query.read(key, at=K2))
    assert isinstance(current, CurrentEvidenceBasis)
    assert stale.changed_positive_references == (
        BasisPositiveChange(
            BasisPositiveRole.TARGET, prior.target.version, current.target.version
        ),
    )
    assert stale.changed_owner_meanings == ()
    assert _revalidate(current, query, key, T3) is None
    witness = asyncio.run(
        IntelligenceJudgmentMeaningReader(store).read_at(
            key,
            TargetJudgmentMeaning(current.target.version),
            effective_at=T3,
            known_at=T3,
            read_at=T3,
        )
    )
    assert isinstance(witness, OwnerMeaningWitness)
    selected = store.history.acts[-1]
    assert witness.provenance.attribution == selected.attribution
    assert witness.provenance.basis == selected.basis
    assert witness.provenance.selected_act_id == selected.act_id
    ancestry_ids = tuple(
        record.fact.act_id for record in witness.cause.correction_ancestry
    )
    assert ancestry_ids == tuple(act.act_id for act in store.history.acts)
    expected_history = tuple(
        OwnerHistoryRecord(act, act.effective_at, act.recorded_at)
        for act in store.history.acts
    )
    assert witness.cause.correction_ancestry == expected_history
    assert witness.cause.fact_ancestry == (expected_history[-1], expected_history[0])
    assert witness.cause.relationship_guards == (
        IntelligenceSelectionGuard(
            key,
            selected.act_id,
            store.history.acts[0].act_id,
            store.history.versions,
            None,
            None,
        ),
    )
    assert store.history.acts[-1].pending_resolutions == (
        PendingResolution(
            IntelligenceJudgmentLane.TARGET,
            store.history.acts[1].act_id,
            PendingDisposition.CANCEL,
        ),
    )
    assert (
        asyncio.run(
            IntelligenceJudgmentMeaningReader(store).verify_cause(
                witness, validation_at=T3
            )
        )
        is OwnerCauseVerdict.VALID
    )


def test_claim_correction_stales_exact_basis_by_claim_and_guard_roles() -> None:
    store = _Store(_initial_with_known_actor())
    initial = store.history.acts[0]
    assert initial.catalog is not None
    claim = initial.catalog.claims[0]
    query, key = _current_query(store)
    prior = asyncio.run(query.read(key, at=K0))
    assert isinstance(prior, CurrentEvidenceBasis)
    correction = replace(
        _catalog_correction(
            store.history, _with_observation_support(claim), "claim support corrected"
        ),
        attribution=KnownActorAttribution(ActorId(uuid4())),
    )
    assert correction.attribution != initial.attribution
    store.history = store.history.append(correction)
    assert store.history.versions[-1][0].value == 1
    assert store.history.versions[-1][1].value == 2
    stale = _revalidate(prior, query, key, K1)
    # duplicate-code: These expected stale roles independently certify the
    # Intelligence owner; sharing Portfolio's expected result would couple proofs.
    # arid: disable
    assert isinstance(stale, StaleEvidenceBasis)
    assert stale.categories == {
        StaleEvidenceBasisCategory.CLAIM_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
    }
    # arid: enable
    assert {change.role for change in stale.changed_positive_references} == {
        BasisPositiveRole.CLAIM
    }
    assert {guard.role for guard in stale.broken_guards} == {
        BasisGuardRole.CLAIM_MEMBERSHIP
    }
    current = asyncio.run(query.read(key, at=K1))
    assert isinstance(current, CurrentEvidenceBasis)
    assert current.owner_meaning.claim is not None
    assert prior.owner_meaning.claim is not None
    assert current.owner_meaning.claim.provenance.attribution == correction.attribution
    assert current.owner_meaning.claim.provenance.basis == correction.basis
    assert current.owner_meaning.claim.provenance.selected_act_id == correction.act_id
    assert current.owner_meaning.claim.cause.correction_ancestry == tuple(
        OwnerHistoryRecord(act, act.effective_at, act.recorded_at)
        for act in store.history.acts
    )
    assert stale.changed_positive_references == (
        BasisPositiveChange(
            BasisPositiveRole.CLAIM,
            prior.claim_catalog_version,
            current.claim_catalog_version,
        ),
    )
    assert stale.changed_owner_meanings == ()
    assert stale.broken_guards == (
        BasisGuardBreak(
            BasisGuardRole.CLAIM_MEMBERSHIP,
            prior.guards.claim,
            current.guards.claim,
        ),
    )


def test_future_catalog_meaning_stales_without_a_new_catalog_version() -> None:
    # duplicate-code: This independent clock-change falsifier needs its own
    # initial owner and query; sharing the committed-correction case would
    # couple the two temporal proofs.
    # arid: disable
    store = _Store(_initial_with_known_actor())
    initial = store.history.acts[0]
    assert initial.catalog is not None
    claim = initial.catalog.claims[0]
    query, key = _current_query(store)
    # arid: enable
    future = replace(
        _catalog_correction(
            store.history,
            _with_observation_support(claim),
            "future claim support corrected",
        ),
        effective_at=T3,
        attribution=KnownActorAttribution(ActorId(uuid4())),
    )
    assert future.attribution != initial.attribution
    store.history = store.history.append(future)
    assert store.history.versions[-1] == store.history.versions[0]
    prior = asyncio.run(query.read(key, at=K1))
    assert isinstance(prior, CurrentEvidenceBasis)
    fresh = asyncio.run(query.read(key, at=T3))
    assert isinstance(fresh, CurrentEvidenceBasis)
    assert prior.claim_catalog_version == fresh.claim_catalog_version
    assert prior.owner_meaning.claim is not None
    assert fresh.owner_meaning.claim is not None
    assert prior.owner_meaning.claim.meaning[0] == claim
    assert fresh.owner_meaning.claim.meaning[0] == future.catalog.claims[0]
    assert fresh.owner_meaning.claim.provenance.attribution == future.attribution
    assert fresh.owner_meaning.claim.provenance.basis == future.basis
    assert fresh.owner_meaning.claim.provenance.selected_act_id == future.act_id
    assert fresh.owner_meaning.claim.cause.correction_ancestry == tuple(
        OwnerHistoryRecord(act, act.effective_at, act.recorded_at)
        for act in store.history.acts
    )
    stale = _revalidate(prior, query, key, T3)
    assert isinstance(stale, StaleEvidenceBasis)
    assert stale.categories == {StaleEvidenceBasisCategory.CLAIM_CHANGED}
    assert stale.changed_positive_references == ()
    assert stale.broken_guards == ()
    assert stale.changed_owner_meanings == (
        BasisOwnerMeaningChange(
            BasisPositiveRole.CLAIM,
            prior.owner_meaning.claim,
            fresh.owner_meaning.claim,
        ),
    )


def test_one_commit_advances_both_changed_current_owner_lanes() -> None:
    store = _Store(_initial())
    initial = store.history.acts[0]
    assert initial.assertion is not None and initial.catalog is not None
    claim = initial.catalog.claims[0]
    store.history = store.history.append(
        _catalog_correction(
            store.history,
            _with_observation_support(claim),
            "target and claim corrected together",
            target_statement="B",
        )
    )
    assert tuple(version.value for version in store.history.versions[-1]) == (2, 2)


def test_missing_claim_and_invalid_history_remain_distinct_from_stale() -> None:
    store = _Store(_initial())
    query, key = _current_query(store)
    prior = asyncio.run(query.read(key, at=K0))
    assert isinstance(prior, CurrentEvidenceBasis)
    store.history = store.history.append(
        _catalog_correction(
            store.history, IntelligenceClaimCatalog(()), "claim withdrawn"
        )
    )
    missing = _revalidate(prior, query, key, K1)
    assert isinstance(missing, CurrentEvidenceNoBasis)
    assert missing.reason is CurrentNoBasisReason.MISSING

    store.invalid = True
    invalid = _revalidate(prior, query, key, K2)
    assert isinstance(invalid, CurrentEvidenceNoBasis)
    assert invalid.reason is CurrentNoBasisReason.INVALID_HISTORY
    witness = asyncio.run(
        IntelligenceJudgmentMeaningReader(store).read_at(
            key,
            TargetJudgmentMeaning(prior.target.version),
            effective_at=K2,
            known_at=K2,
            read_at=K2,
        )
    )
    assert isinstance(witness, OwnerMeaningNoBasis)
    assert witness.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY
