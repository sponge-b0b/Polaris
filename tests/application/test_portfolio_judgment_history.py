from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

import pytest

from polaris.application.evidence.claims import (
    ClaimNotCurrent,
    InvalidClaimHistory,
    InvalidClaimReference,
    ResolvedClaimMembership,
)
from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceBasisQuery,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
)
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentInvalidHistory,
    TargetJudgmentMissing,
    TargetJudgmentNotYetEffective,
    TargetJudgmentResolver,
)
from polaris.application.evidence.owner_meaning import (
    ClaimMembershipMeaning,
    OwnerCauseVerdict,
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
from polaris.application.evidence.requirements import (
    ResolvedEvidenceRequirementVersion,
)
from polaris.application.evidence.revalidation import (
    AtomicCurrentBasisRead,
    CurrentEvidenceBasisRevalidator,
)
from polaris.application.portfolio_judgment_history import (
    PortfolioJudgmentClaimResolver,
    PortfolioJudgmentMeaningReader,
    PortfolioJudgmentTargetReader,
)
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import BasisScopeKey
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceUse,
    JudgmentWideEvidenceScope,
)
from polaris.domain.evidence.observations import EvidenceObservationId
from polaris.domain.evidence.sufficiency import (
    EvidenceRequirementDisposition,
    evaluate_evidence_sufficiency,
)
from polaris.domain.portfolio_judgment_history import (
    PendingDisposition,
    PendingResolution,
    PortfolioClaimCatalog,
    PortfolioJudgmentAct,
    PortfolioJudgmentHistory,
    PortfolioJudgmentLane,
)
from polaris.infrastructure.persistence.postgresql.portfolio_judgment_history import (
    _act_from_row,
    _act_values,
)
from tests.application.evidence.test_current_basis import _query
from tests.domain.configuration.configuration_support import (
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.domain.evidence.sufficiency_support import (
    ASSESSMENT_EFFECTIVE_AT,
    ASSESSMENT_KNOWN_AT,
    interpreted_binding,
)
from tests.domain.test_portfolio_judgment_history import (
    K0,
    K1,
    K2,
    T3,
    _correction,
    _history,
)


class _Store:
    def __init__(self, history: PortfolioJudgmentHistory) -> None:
        self.history = history
        self.invalid = False

    async def load(self, root):
        if self.invalid:
            raise ValueError("incomplete Portfolio judgment act payload")
        return self.history if self.history.acts[0].root == root else None

    async def append(self, act):
        self.history = self.history.append(act)
        return self.history


class _PortfolioParticipation:
    def __init__(
        self, query: CurrentEvidenceBasisQuery, key: BasisScopeKey, at: datetime
    ) -> None:
        self.query = query
        self.key = key
        self.at = at

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead:
        assert key == self.key
        return AtomicCurrentBasisRead(key, self.at, self.query)


def _portfolio_current_query(store: _Store, claim_id: ClaimId):
    root = store.history.acts[0].root
    applicability = replace(
        requirement_key(), target=root, scope=ClaimSpecificEvidenceScope(claim_id)
    )
    initial = asyncio.run(
        PortfolioJudgmentTargetReader(store).read_at(root, effective_at=K0, known_at=K0)
    )
    assert isinstance(initial, ResolvedTargetJudgment)
    query, key, *_ = _query(
        applicability_key=applicability,
        empty=True,
        target_version=initial.version,
    )
    query._targets = TargetJudgmentResolver(PortfolioJudgmentTargetReader(store))
    query._claims = PortfolioJudgmentClaimResolver(store)
    owner = OwnerMeaningResolver(PortfolioJudgmentMeaningReader(store))
    query._target_meaning = owner
    query._claim_meaning = owner

    class _Requirements:
        async def resolve(self, request, *, effective_at, known_at):
            assert request == applicability
            assert effective_at <= known_at
            version = requirement_version(
                assignment=requirement_assignment_for_key(applicability)
            )
            return ResolvedEvidenceRequirementVersion(version)

    query._requirements = _Requirements()
    return query, key


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_owner_reads_bind_target_catalog_versions_and_temporal_cause(
    family: str,
) -> None:
    store = _Store(_history(family))
    root = store.history.acts[0].root
    target_reader = PortfolioJudgmentTargetReader(store)
    claim_reader = PortfolioJudgmentClaimResolver(store)
    meaning_reader = PortfolioJudgmentMeaningReader(store)
    claim_id = ClaimId(uuid4())
    initial_target = asyncio.run(
        target_reader.read_at(root, effective_at=K0, known_at=K0)
    )
    assert isinstance(initial_target, ResolvedTargetJudgment)
    future = _correction(
        store.history,
        effective_at=T3,
        known_at=K1,
        scenario="B",
        proposition="future",
    )
    store.history = store.history.append(future)
    initial_again = asyncio.run(
        target_reader.read_at(root, effective_at=K1, known_at=K1)
    )
    assert isinstance(initial_again, ResolvedTargetJudgment)
    assert initial_again.version == initial_target.version
    assert initial_again.assertion == initial_target.assertion
    future_read = asyncio.run(target_reader.read_at(root, effective_at=T3, known_at=K1))
    assert isinstance(future_read, ResolvedTargetJudgment)
    assert future_read.assertion == future.assertion
    immediate = _correction(
        store.history,
        effective_at=K2,
        known_at=K2,
        scenario="C",
        proposition="current",
        disposition=PendingDisposition.RETAIN,
    )
    store.history = store.history.append(immediate)
    at_t3 = asyncio.run(target_reader.read_at(root, effective_at=T3, known_at=T3))
    assert isinstance(at_t3, ResolvedTargetJudgment)
    assert at_t3.assertion == future.assertion
    assert at_t3.version.revision.value == 2
    assert tuple(item.act_id for item in at_t3.correction_support) == (
        store.history.acts[0].act_id,
        future.act_id,
    )

    known_claim = immediate.catalog.claims[0].claim_id
    membership = asyncio.run(
        claim_reader.resolve(root, known_claim, effective_at=K2, known_at=K2)
    )
    assert isinstance(membership, ResolvedClaimMembership)
    assert membership.catalog_version.value == 2
    absent = asyncio.run(
        claim_reader.resolve(root, claim_id, effective_at=K2, known_at=K2)
    )
    assert isinstance(absent, InvalidClaimReference)

    # duplicate-code: this Portfolio witness key is an independent owner proof;
    # sharing setup with a Decisions test would couple their falsifiers.
    # arid: disable
    key = BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        root,
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )
    # arid: enable
    target_subject = TargetJudgmentMeaning(initial_target.version)
    initial_witness = asyncio.run(
        meaning_reader.read_at(
            key,
            target_subject,
            effective_at=K1,
            known_at=K1,
            read_at=K1,
        )
    )
    assert isinstance(initial_witness, OwnerMeaningWitness)
    changed_witness = asyncio.run(
        meaning_reader.read_at(
            key,
            target_subject,
            effective_at=K2,
            known_at=K2,
            read_at=K2,
        )
    )
    assert isinstance(changed_witness, OwnerMeaningWitness)
    assert changed_witness.semantic_identity != initial_witness.semantic_identity
    assert len(changed_witness.cause.correction_ancestry) == 3
    assert (
        asyncio.run(meaning_reader.verify_cause(initial_witness, validation_at=K2))
        is OwnerCauseVerdict.VALID
    )

    claim_key = replace(key, scope=ClaimSpecificEvidenceScope(known_claim))
    claim_subject = ClaimMembershipMeaning(
        root, known_claim, membership.catalog_version
    )
    claim_witness = asyncio.run(
        meaning_reader.read_at(
            claim_key,
            claim_subject,
            effective_at=K2,
            known_at=K2,
            read_at=K2,
        )
    )
    assert isinstance(claim_witness, OwnerMeaningWitness)
    assert claim_witness.cause.relationship_guards[0].claim_selected

    wrong_root = replace(root, value=uuid4())
    before_effective = asyncio.run(
        target_reader.read_at(root, effective_at=K0.replace(day=19), known_at=K0)
    )
    assert isinstance(before_effective, TargetJudgmentNotYetEffective)
    assert isinstance(
        asyncio.run(target_reader.read_at(wrong_root, effective_at=K2, known_at=K2)),
        TargetJudgmentMissing,
    )
    no_basis = asyncio.run(
        meaning_reader.read_at(
            replace(key, target=wrong_root),
            TargetJudgmentMeaning(replace(initial_target.version, root=wrong_root)),
            effective_at=K2,
            known_at=K2,
            read_at=K2,
        )
    )
    assert isinstance(no_basis, OwnerMeaningNoBasis)
    assert no_basis.reason is OwnerMeaningNoBasisReason.MISSING


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_persistence_act_payload_round_trips_typed_meaning(family: str) -> None:
    history = _history(family)
    root = history.acts[0].root
    for index, act in enumerate(history.acts):
        row = _act_values(act, index + 1, *history.versions[index])
        assert _act_from_row(row) == act
    wrong_root = replace(root, value=uuid4())
    row = _act_values(history.acts[0], 1, *history.versions[0])
    if family == "consequence":
        row["consequence_id"] = wrong_root.value
    else:
        row["assessment_id"] = wrong_root.value
    with pytest.raises(ValueError, match="typed root"):
        _act_from_row(row)
    incomplete = _act_values(history.acts[0], 1, *history.versions[0])
    payload = incomplete["act"]
    assert isinstance(payload, dict)
    incomplete["act"] = {key: value for key, value in payload.items() if key != "basis"}
    with pytest.raises(ValueError, match="incomplete Portfolio judgment act"):
        _act_from_row(incomplete)


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_incomplete_owner_history_returns_typed_invalid_outcomes(family: str) -> None:
    history = _history(family)
    root = history.acts[0].root
    catalog = history.acts[0].catalog
    assert catalog is not None

    class _InvalidStore(_Store):
        async def load(self, root):
            raise ValueError("incomplete Portfolio judgment act payload")

    store = _InvalidStore(history)
    target = asyncio.run(
        PortfolioJudgmentTargetReader(store).read_at(root, effective_at=K0, known_at=K0)
    )
    assert isinstance(target, TargetJudgmentInvalidHistory)
    claim_id = catalog.claims[0].claim_id
    claim = asyncio.run(
        PortfolioJudgmentClaimResolver(store).resolve(
            root, claim_id, effective_at=K0, known_at=K0
        )
    )
    assert isinstance(claim, InvalidClaimHistory)
    # duplicate-code: this malformed-history key is constructed independently
    # of valid owner proof so both failure paths keep distinct falsifiers.
    # arid: disable
    key = BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        root,
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )
    # arid: enable
    valid_target = asyncio.run(
        PortfolioJudgmentTargetReader(_Store(history)).read_at(
            root, effective_at=K0, known_at=K0
        )
    )
    assert isinstance(valid_target, ResolvedTargetJudgment)
    subject = TargetJudgmentMeaning(valid_target.version)
    witness = asyncio.run(
        PortfolioJudgmentMeaningReader(store).read_at(
            key, subject, effective_at=K0, known_at=K0, read_at=K0
        )
    )
    assert isinstance(witness, OwnerMeaningNoBasis)
    assert witness.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_catalog_support_change_and_removed_claim_have_distinct_owner_results(
    family: str,
) -> None:
    store = _Store(_history(family))
    root = store.history.acts[0].root
    initial_catalog = store.history.acts[0].catalog
    assert initial_catalog is not None
    claim = initial_catalog.claims[0]
    resolver = PortfolioJudgmentClaimResolver(store)
    meaning = PortfolioJudgmentMeaningReader(store)
    key = BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        root,
        ClaimSpecificEvidenceScope(claim.claim_id),
        EvidenceUse.JUDGMENT_BASIS,
    )
    subject = ClaimMembershipMeaning(root, claim.claim_id, store.history.versions[0][1])
    prior = asyncio.run(
        meaning.read_at(key, subject, effective_at=K0, known_at=K0, read_at=K0)
    )
    assert isinstance(prior, OwnerMeaningWitness)
    change = _correction(
        store.history,
        effective_at=K1,
        known_at=K1,
        scenario="support",
        proposition=claim.proposition,
    )
    assert change.catalog is not None
    changed_support = change.catalog.claims[0].surviving_support
    changed_claim = replace(claim, surviving_support=changed_support)
    change = replace(
        change,
        catalog=PortfolioClaimCatalog((changed_claim,)),
    )
    store.history = store.history.append(change)
    current = asyncio.run(
        resolver.resolve(root, claim.claim_id, effective_at=K1, known_at=K1)
    )
    assert isinstance(current, ResolvedClaimMembership)
    assert current.catalog_version.value == 2
    fresh = asyncio.run(
        meaning.read_at(key, subject, effective_at=K1, known_at=K1, read_at=K1)
    )
    assert isinstance(fresh, OwnerMeaningWitness)
    assert fresh.semantic_identity != prior.semantic_identity
    assert fresh.cause.relationship_guards[0].claim_selected

    removal = _correction(
        store.history,
        effective_at=K2,
        known_at=K2,
        scenario="removed",
        proposition="replacement proposition",
    )
    removal = replace(
        removal,
        target_predecessor=change.act_id,
        catalog_predecessor=change.act_id,
    )
    store.history = store.history.append(removal)
    absent = asyncio.run(
        resolver.resolve(root, claim.claim_id, effective_at=K2, known_at=K2)
    )
    assert isinstance(absent, ClaimNotCurrent)


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_target_correction_stales_dependent_write_without_changing_claim_catalog(
    family: str,
) -> None:
    # duplicate-code: target and catalog correction proofs independently
    # establish their protected prior basis so neither can mask the other.
    # arid: disable
    store = _Store(_history(family))
    initial = store.history.acts[0]
    assert initial.catalog is not None
    claim = initial.catalog.claims[0]
    query, key = _portfolio_current_query(store, claim.claim_id)
    prior = asyncio.run(query.read(key, at=K0))
    assert isinstance(prior, CurrentEvidenceBasis)
    # arid: enable

    # duplicate-code: this target-only future act independently tests lane
    # selection; sharing the full owner-read scenario would couple proofs.
    # arid: disable
    future = replace(
        _correction(
            store.history,
            effective_at=T3,
            known_at=K1,
            scenario="B",
            proposition=claim.proposition,
        ),
        catalog=None,
        catalog_predecessor=None,
        compatible_opposite_acts=(initial.act_id,),
    )
    # arid: enable
    store.history = store.history.append(future)
    assert isinstance(asyncio.run(query.read(key, at=K1)), CurrentEvidenceBasis)
    assert (
        asyncio.run(
            CurrentEvidenceBasisRevalidator().revalidate(
                prior, _PortfolioParticipation(query, key, K1)
            )
        )
        is None
    )

    # duplicate-code: explicit target-lane cancellation must remain visible
    # apart from the owner-read test's dual-lane correction scenario.
    # arid: disable
    immediate = replace(
        _correction(
            store.history,
            effective_at=K2,
            known_at=K2,
            scenario="C",
            proposition=claim.proposition,
            disposition=PendingDisposition.CANCEL,
        ),
        catalog=None,
        catalog_predecessor=None,
        pending_resolutions=(
            PendingResolution(
                PortfolioJudgmentLane.TARGET,
                future.act_id,
                PendingDisposition.CANCEL,
            ),
        ),
        compatible_opposite_acts=(initial.act_id,),
    )
    # arid: enable
    store.history = store.history.append(immediate)
    fresh = asyncio.run(query.read(key, at=K2))
    assert isinstance(fresh, CurrentEvidenceBasis)
    assert fresh.target.version != prior.target.version
    assert fresh.guards.claim == prior.guards.claim
    writes: list[str] = []

    async def dependent_write() -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
        outcome = await CurrentEvidenceBasisRevalidator().revalidate(
            prior, _PortfolioParticipation(query, key, K2)
        )
        if outcome is None:
            writes.append("dependent judgment")
        return outcome

    stale = asyncio.run(dependent_write())
    assert isinstance(stale, StaleEvidenceBasis)
    assert stale.categories == {StaleEvidenceBasisCategory.TARGET_CHANGED}
    assert writes == []


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_portfolio_catalog_correction_stales_exact_evidence_basis_and_blocks_write(
    family: str,
) -> None:
    store = _Store(_history(family))
    initial = store.history.acts[0]
    assert initial.catalog is not None
    claim = initial.catalog.claims[0]
    query, key = _portfolio_current_query(store, claim.claim_id)
    prior = asyncio.run(query.read(key, at=K0))
    assert isinstance(prior, CurrentEvidenceBasis)

    # duplicate-code: this catalog-only act is an independent Evidence stale
    # basis falsifier, separate from domain target-lane selection proof.
    # arid: disable
    future = PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        "future claim support",
        T3,
        K1,
        K1,
        (initial.act_id,),
        catalog=PortfolioClaimCatalog((replace(claim, surviving_support=frozenset()),)),
        catalog_predecessor=initial.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    # arid: enable
    store.history = store.history.append(future)
    unchanged = asyncio.run(query.read(key, at=K1))
    assert isinstance(unchanged, CurrentEvidenceBasis)
    assert unchanged.target.version == prior.target.version
    assert unchanged.guards.claim == prior.guards.claim
    current = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            prior, _PortfolioParticipation(query, key, K1)
        )
    )
    assert current is None

    immediate = PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        "current claim support",
        K2,
        K2,
        K2,
        (initial.act_id, future.act_id),
        catalog=PortfolioClaimCatalog(
            (
                replace(
                    claim,
                    surviving_support=frozenset({EvidenceObservationId(uuid4())}),
                ),
            )
        ),
        catalog_predecessor=initial.act_id,
        pending_resolutions=(
            PendingResolution(
                PortfolioJudgmentLane.CATALOG,
                future.act_id,
                PendingDisposition.CANCEL,
            ),
        ),
        compatible_opposite_acts=(initial.act_id,),
    )
    store.history = store.history.append(immediate)
    writes: list[str] = []

    async def dependent_write(at: datetime):
        outcome = await CurrentEvidenceBasisRevalidator().revalidate(
            prior, _PortfolioParticipation(query, key, at)
        )
        if outcome is None:
            writes.append("dependent judgment")
        return outcome

    stale = asyncio.run(dependent_write(K2))
    assert isinstance(stale, StaleEvidenceBasis)
    assert stale.categories == {
        StaleEvidenceBasisCategory.CLAIM_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
    }
    assert writes == []

    removal = PortfolioJudgmentAct(
        uuid4(),
        initial.root,
        initial.attribution,
        "claim removed",
        T3,
        T3,
        T3,
        (initial.act_id, future.act_id, immediate.act_id),
        catalog=PortfolioClaimCatalog(()),
        catalog_predecessor=immediate.act_id,
        compatible_opposite_acts=(initial.act_id,),
    )
    store.history = store.history.append(removal)
    absent = asyncio.run(query.read(key, at=T3))
    assert isinstance(absent, CurrentEvidenceNoBasis)
    assert absent.reason is CurrentNoBasisReason.MISSING
    absent_write = asyncio.run(dependent_write(T3))
    assert isinstance(absent_write, CurrentEvidenceNoBasis)
    assert absent_write.reason is CurrentNoBasisReason.MISSING
    assert writes == []

    store.invalid = True
    invalid = asyncio.run(query.read(key, at=T3))
    assert isinstance(invalid, CurrentEvidenceNoBasis)
    assert invalid.reason is CurrentNoBasisReason.INVALID_HISTORY
    rejected = asyncio.run(dependent_write(T3))
    assert isinstance(rejected, CurrentEvidenceNoBasis)
    assert rejected.reason is CurrentNoBasisReason.INVALID_HISTORY
    assert writes == []


@pytest.mark.parametrize("family", ["consequence", "risk"])
def test_claim_scoped_sufficiency_counts_observations_with_binding_proof(
    family: str,
) -> None:
    # duplicate-code: sufficiency derives its own target claim before testing
    # observation counting; sharing invalid-history setup hides that proof.
    # arid: disable
    history = _history(family)
    root = history.acts[0].root
    catalog = history.acts[0].catalog
    assert catalog is not None
    claim_id = catalog.claims[0].claim_id
    # arid: enable
    key = replace(
        requirement_key(),
        target=root,
        scope=ClaimSpecificEvidenceScope(claim_id),
    )
    version = requirement_version(
        minimum_distinct_observations=2,
        assignment=requirement_assignment_for_key(key),
    )

    def for_key(ordinal: int, observation: int):
        original = interpreted_binding(ordinal, observation_ordinal=observation)
        freshness = original.binding.freshness
        changed = replace(
            original.binding,
            target=root,
            scope=key.scope,
            freshness=replace(
                freshness,
                basis=replace(freshness.basis, applicability_key=key),
            ),
        )
        return replace(
            original,
            binding=changed,
            surviving_bindings=frozenset({changed}),
        )

    first = for_key(1, 9)
    duplicate = for_key(2, 9)
    other = for_key(3, 10)
    deficient = evaluate_evidence_sufficiency(
        version,
        key,
        (first, duplicate),
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
    ).requirement_assessments[0]
    assert deficient.disposition is EvidenceRequirementDisposition.MISSING
    assert deficient.counted_observation_ids == frozenset(
        {first.binding.observation_id}
    )
    assert {proof.binding_id for proof in deficient.binding_proofs} == {
        first.binding.binding_id,
        duplicate.binding.binding_id,
    }
    sufficient = evaluate_evidence_sufficiency(
        version,
        key,
        (first, duplicate, other),
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
    ).requirement_assessments[0]
    assert sufficient.disposition is EvidenceRequirementDisposition.SATISFIED
    assert sufficient.counted_observation_ids == frozenset(
        {first.binding.observation_id, other.binding.observation_id}
    )
    assert len(sufficient.binding_proofs) == 3
