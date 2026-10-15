from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.decisions.memory import (
    DecisionMemoryCurrentState,
    DecisionMemoryService,
)
from polaris.application.decisions.owner_meaning import DecisionOwnerMeaningReader
from polaris.application.evidence.claims import ResolvedClaimMembership
from polaris.application.evidence.context_versions import (
    CompleteContextSelection,
    ContextContribution,
    ContextNoBasis,
    ContextNoBasisReason,
    ContextSelectionResolver,
    ResolvedContextSelection,
    SelectedContextFact,
)
from polaris.application.evidence.current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceBasisQuery,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
    EvidenceHistoryInvalid,
    ResolvedRequirementKey,
)
from polaris.application.evidence.judgment_versions import (
    ResolvedTargetJudgment,
    TargetJudgmentResolver,
    TargetJudgmentUnavailable,
)
from polaris.application.evidence.owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    ClaimMembershipMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from polaris.application.evidence.reconstruction import (
    EvidenceHistories,
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from polaris.application.evidence.requirements import (
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
)
from polaris.application.evidence.revalidation import (
    AtomicCurrentBasisRead,
    AtomicCurrentBasisUnavailable,
    CurrentEvidenceBasisRevalidator,
)
from polaris.application.evidence.sufficiency import EvidenceSufficiencyBasis
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementSetVersion,
    InvestmentHorizon,
)
from polaris.domain.decisions import (
    DecisionApplicability,
    DecisionMutationContext,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    InvestmentDecision,
    withdraw_decision_work,
)
from polaris.domain.decisions.facts import DecisionLifecycleFactId, OperationId
from polaris.domain.evidence import (
    ClaimCatalogVersion,
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceAssessmentCorrection,
    EvidenceAssessmentCorrectionHistory,
    EvidenceBindingCorrection,
    EvidenceBindingCorrectionHistory,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceJudgmentFamily,
    EvidenceObservation,
    EvidenceObservationCorrection,
    EvidenceObservationCorrectionHistory,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSupportVersion,
    EvidenceUse,
    evidence_judgment_ref,
)
from polaris.domain.evidence.bindings import EvidenceRole
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    CanonicalContextVersionRef,
    ContextRootRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
    context_root,
)
from polaris.domain.evidence.judgment_versions import (
    DecisionEvaluationVersionRef,
    HumanInvestmentDecisionVersionRef,
    InvestmentHypothesisVersionRef,
    InvestmentRecommendationVersionRef,
    InvestmentViewVersionRef,
    JudgmentRevision,
    LessonVersionRef,
    MeaningfulChallengeResultVersionRef,
    PortfolioRiskAssessmentVersionRef,
    ProjectedPortfolioConsequenceVersionRef,
    RecommendationWithholdingJudgmentVersionRef,
    TargetJudgmentVersionRef,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingUniverseGuard,
    EvidenceCorrectionUniverseGuard,
    EvidenceRequirementAuthorityGuard,
    EvidenceSufficiencyBasisGuards,
)
from tests.application.decisions.test_memory import _future_relationship_owner
from tests.application.evidence.test_context_versions import _OWNER_FAMILY_CASES
from tests.application.evidence.test_reconstruction import _decision
from tests.configuration_support import (
    SECOND_VERSION_ID,
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.sufficiency_support import derived_assessment, interpreted_binding

AT = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)


class _DecisionStore:
    def __init__(self, decision: InvestmentDecision) -> None:
        self.decision = decision
        self.at: datetime | None = None
        self.history_override: tuple | None = None

    async def load_current_decision_state(
        self, decision_id: object, *, known_at: datetime
    ) -> DecisionMemoryCurrentState | None:
        self.at = known_at
        if decision_id != self.decision.decision_id:
            return None
        return DecisionMemoryCurrentState(
            self.history_override or self.decision.history, self.decision.version, ()
        )

    async def load_relationship_history(self) -> tuple:
        return ()


class _Targets:
    def __init__(self, result: object) -> None:
        self.result = result
        self.received: tuple | None = None

    async def read_at(
        self, target: object, *, effective_at: datetime, known_at: datetime
    ) -> object:
        self.received = (target, effective_at, known_at)
        return self.result


@dataclass(frozen=True, slots=True)
class _Relationship:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: ContextRootRef
    revision: int


@dataclass(frozen=True, slots=True)
class _Universe:
    key: BasisScopeKey
    role: ContextSelectionRole
    revision: int


class _Contexts:
    def __init__(self) -> None:
        self.selected: dict[ContextSelectionRole, tuple[SelectedContextFact, ...]] = {}
        self.revision = 1
        self.calls: list[tuple] = []
        self.failure: ContextNoBasisReason | None = None

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ResolvedContextSelection:
        self.calls.append((key, role, effective_at, known_at))
        if self.failure is not None:
            return ContextNoBasis(
                key, role, effective_at, known_at, self.failure, "context failure"
            )
        facts = self.selected.get(role, ())
        roots = frozenset(context_root(fact.reference) for fact in facts)
        guard = ContextSelectionGuard(
            key,
            role,
            roots,
            frozenset(_Relationship(key, role, root, self.revision) for root in roots),
            _Universe(key, role, self.revision),
        )
        return ResolvedContextSelection(key, role, effective_at, known_at, facts, guard)


class _RequirementKeys:
    def __init__(self, applicability_key: EvidenceRequirementApplicabilityKey) -> None:
        self.applicability_key = applicability_key

    async def read_current(
        self,
        key: BasisScopeKey,
        target: ResolvedTargetJudgment,
        context: CompleteContextSelection,
        *,
        at: datetime,
    ) -> ResolvedRequirementKey:
        assert target.target == key.target
        assert context.key == key
        return ResolvedRequirementKey(key, at, self.applicability_key)


class _Sufficiency:
    def __init__(
        self,
        version: EvidenceSupportVersion,
        applicability_key: EvidenceRequirementApplicabilityKey,
        *,
        empty: bool = False,
        result: object | None = None,
    ) -> None:
        self.version = version
        self.applicability_key = applicability_key
        self.empty = empty
        self.result = result
        self.interpretations_override: tuple | None = None
        self.authority_override: EvidenceRequirementSetVersion | None = None

    async def load_sufficiency_basis(
        self,
        applicability_key: object,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSufficiencyBasis:
        assert applicability_key == self.applicability_key
        assert effective_at == known_at
        if self.result is not None:
            return self.result
        interpreted = (
            self.interpretations_override
            if self.interpretations_override is not None
            else ()
            if self.empty
            else (interpreted_binding(),)
        )
        authority = self.authority_override or replace(
            requirement_version(),
            applicability=requirement_assignment_for_key(self.applicability_key),
        )
        return EvidenceSufficiencyBasis(
            authority,
            interpreted,
            self.version,
            EvidenceSufficiencyBasisGuards(
                EvidenceBindingUniverseGuard(
                    frozenset(item.binding.binding_id for item in interpreted)
                ),
                EvidenceCorrectionUniverseGuard(
                    frozenset(
                        fact
                        for item in interpreted
                        for fact in item.fact_support
                        if type(fact) is EvidenceCorrectionId
                    )
                ),
                EvidenceRequirementAuthorityGuard(frozenset({authority.version_id})),
            ),
        )


class _Evidence:
    def __init__(self, histories: EvidenceHistories, target: object) -> None:
        self.histories = histories
        self.target = target

    async def load_scope_histories(
        self, key: BasisScopeKey, *, at: datetime
    ) -> EvidenceHistories:
        assert key.target == self.target
        assert at.tzinfo is not None
        return self.histories


class _Epochs:
    def __init__(self, version: EvidenceSupportVersion) -> None:
        self.version = version
        self.calls: list[tuple] = []

    async def load_support_version(
        self,
        target: object,
        scope: object,
        evidence_use: object,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> EvidenceSupportVersion:
        self.calls.append((target, scope, evidence_use, effective_at, known_at))
        return self.version


class _Claims:
    def __init__(self, result: object | None = None) -> None:
        self.result = result

    async def resolve(self, *args: object, **kwargs: object) -> object:
        if self.result is None:
            raise AssertionError("judgment-wide scope has no claim membership read")
        return self.result


class _MeaningOwner:
    """Downstream owner double with a verifiable exact current-read projection."""

    def __init__(self, target: _Targets, contexts: _Contexts, claims: _Claims) -> None:
        self.target = target
        self.contexts = contexts
        self.claims = claims
        self.failure: OwnerMeaningNoBasisReason | None = None
        self.failure_for: type | None = None
        self.override: OwnerMeaningWitness | None = None
        self.override_for: type | None = None
        self.future_fact_at: datetime | None = None
        self.meaning_at: dict[OwnerMeaningSubject, tuple[datetime, object]] = {}
        self.calls: list[OwnerMeaningSubject] = []

    def _expected(
        self, key: BasisScopeKey, subject: OwnerMeaningSubject, at: datetime
    ) -> OwnerMeaningWitness:
        if isinstance(subject, TargetJudgmentMeaning):
            assert isinstance(self.target.result, ResolvedTargetJudgment)
            meaning: object = (
                self.target.result.assertion,
                self.target.result.correction_support,
            )
        elif isinstance(subject, ClaimMembershipMeaning):
            meaning = self.claims.result
        elif isinstance(subject, CanonicalContextMeaning):
            meaning = next(
                fact
                for fact in self.contexts.selected[subject.role]
                if fact.reference == subject.reference
            )
        else:
            assert isinstance(subject, CanonicalContextAbsence)
            meaning = ()
        transition = self.meaning_at.get(subject)
        if transition is not None and at >= transition[0]:
            meaning = transition[1]
        guards = (
            (subject.selection,)
            if isinstance(subject, (CanonicalContextMeaning, CanonicalContextAbsence))
            else (subject,)
        )
        ancestry: tuple[OwnerHistoryRecord, ...] = (
            OwnerHistoryRecord(subject, AT, AT),
        )
        if self.future_fact_at is not None:
            ancestry += (
                OwnerHistoryRecord(("known future", subject), self.future_fact_at, AT),
            )
        return OwnerMeaningWitness(
            key,
            subject,
            at,
            at,
            at,
            meaning,
            "downstream owner",
            OwnerMeaningCause(ancestry, (), guards, True),
        )

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> OwnerMeaningWitness | OwnerMeaningNoBasis:
        assert effective_at == known_at == read_at
        self.calls.append(subject)
        if self.failure is not None and (
            self.failure_for is None or type(subject) is self.failure_for
        ):
            # duplicate-code: the downstream owner double constructs its own
            # typed failure independently of the concrete Decisions owner.
            # arid: disable
            return OwnerMeaningNoBasis(
                key,
                subject,
                effective_at,
                known_at,
                read_at,
                # arid: enable
                self.failure,
                "owner proof failure",
            )
        if self.override is not None and type(subject) is self.override_for:
            return self.override
        return self._expected(key, subject, read_at)

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        if witness != self._expected(witness.key, witness.subject, witness.read_at):
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        return OwnerCauseVerdict.VALID


# duplicate-code: this current-basis fake independently fixes historical Configuration
# authority;
# sharing the historical-query fake would couple separate proofs.
# arid: disable


class _Requirements:
    async def resolve(
        self,
        key: EvidenceRequirementApplicabilityKey,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ResolvedEvidenceRequirementVersion:
        assert key == requirement_key()
        assert effective_at <= known_at
        return ResolvedEvidenceRequirementVersion(requirement_version())


def _histories() -> EvidenceHistories:
    binding = interpreted_binding().binding
    observation = EvidenceObservation(
        binding.observation_id,
        EvidenceSourceProvenance("provider", "release", "publisher"),
        requirement_key().subject,
        # arid: enable
        # duplicate-code: this current-basis fixture independently constructs
        # observation ancestry;
        # sharing historical-query construction would couple separate proofs.
        # arid: disable
        binding.effective_at,
        binding.effective_at,
        EvidenceObservationMaterial(retained_representation="100"),
        binding.effective_at,
    )
    return EvidenceHistories(
        (EvidenceObservationCorrectionHistory(observation, binding.recorded_at, ()),),
        (EvidenceBindingCorrectionHistory(binding, ()),),
        (),
    )


def _query(
    *,
    decision: InvestmentDecision | None = None,
    histories: EvidenceHistories | None = None,
    # arid: enable
    version: EvidenceSupportVersion | None = None,
    applicability_key: EvidenceRequirementApplicabilityKey | None = None,
    empty: bool = False,
    claim_result: object | None = None,
    target_version: TargetJudgmentVersionRef | None = None,
) -> tuple[
    CurrentEvidenceBasisQuery,
    BasisScopeKey,
    _Targets,
    _Contexts,
    _Epochs,
    _DecisionStore,
]:
    decision = decision or _decision()
    applicability_key = applicability_key or requirement_key()
    owner = _DecisionStore(decision)
    key = BasisScopeKey(
        decision.decision_id,
        applicability_key.target,
        applicability_key.scope,
        applicability_key.evidence_use,
    )
    target = _Targets(
        ResolvedTargetJudgment(
            key.target,
            target_version
            or InvestmentRecommendationVersionRef(key.target, JudgmentRevision(1)),
            "judgment",
            ("owner provenance",),
            AT,
            AT,
        )
    )
    contexts = _Contexts()
    claims = _Claims(claim_result)
    meaning_owner = _MeaningOwner(target, contexts, claims)
    version = version or EvidenceSupportVersion(1)
    epochs = _Epochs(version)
    query = CurrentEvidenceBasisQuery(
        decisions=DecisionMemoryService(reader=owner),
        decision_meaning=DecisionOwnerMeaningReader(owner),
        targets=TargetJudgmentResolver(target),
        target_meaning=meaning_owner,
        contexts=ContextSelectionResolver(contexts),
        context_meaning=meaning_owner,
        requirement_keys=_RequirementKeys(applicability_key),
        sufficiency=_Sufficiency(version, applicability_key, empty=empty),
        evidence=_Evidence(
            histories if histories is not None else _histories(), key.target
        ),
        support_epochs=epochs,
        claims=claims,
        claim_meaning=meaning_owner,
        requirements=_Requirements(),
    )
    return query, key, target, contexts, epochs, owner


def _complete_current(
    query: CurrentEvidenceBasisQuery, key: BasisScopeKey, *, at: datetime = AT
) -> CurrentEvidenceBasis:
    result = asyncio.run(query.read(key, at=at))
    assert isinstance(result, CurrentEvidenceBasis)
    return result


class _AtomicParticipation:
    def __init__(self, read: AtomicCurrentBasisRead | None) -> None:
        self.read = read
        self.keys: list[BasisScopeKey] = []

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead | None:
        self.keys.append(key)
        return self.read


class _UnavailableParticipation:
    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead:
        raise AtomicCurrentBasisUnavailable("target owner cannot join the write")


class _RevalidationReads:
    def __init__(
        self,
        prior: CurrentEvidenceBasis,
        fresh: CurrentEvidenceBasis | CurrentEvidenceNoBasis,
    ) -> None:
        self.results = [prior, fresh]
        self.reads: list[datetime] = []
        self.verified: list[CurrentEvidenceBasis] = []

    async def read(
        self, key: BasisScopeKey, *, at: datetime
    ) -> CurrentEvidenceBasis | CurrentEvidenceNoBasis:
        self.reads.append(at)
        result = self.results.pop(0)
        assert result.key == key and result.at == at
        return result

    async def verify_owner_meaning(
        self, basis: CurrentEvidenceBasis, *, validation_at: datetime
    ) -> None:
        self.verified.append(basis)


def _revalidate_scripted(
    prior: CurrentEvidenceBasis, reads: _RevalidationReads
) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
    later = AT + timedelta(seconds=1)
    return asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            prior,
            _AtomicParticipation(AtomicCurrentBasisRead(prior.key, later, reads)),
        )
    )


class _TimestampedTargets(_Targets):
    async def read_at(
        self, target: object, *, effective_at: datetime, known_at: datetime
    ) -> object:
        result = await super().read_at(
            target, effective_at=effective_at, known_at=known_at
        )
        assert isinstance(result, ResolvedTargetJudgment)
        return replace(result, effective_at=effective_at, known_at=known_at)


def _enroll_temporal_target(query: CurrentEvidenceBasisQuery, target: _Targets) -> None:
    temporal = _TimestampedTargets(target.result)
    query._targets = TargetJudgmentResolver(temporal)
    query._target_meaning._owner.target = temporal


def _revalidate_at(
    query: CurrentEvidenceBasisQuery, prior: CurrentEvidenceBasis, later: datetime
) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
    return asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            prior,
            _AtomicParticipation(AtomicCurrentBasisRead(prior.key, later, query)),
        )
    )


def _empty_temporal_basis() -> tuple[
    CurrentEvidenceBasisQuery, BasisScopeKey, CurrentEvidenceBasis
]:
    query, key, target, *_ = _empty_query(requirement_key())
    _enroll_temporal_target(query, target)
    return query, key, _complete_current(query, key)


def _future_decision_temporal_basis(
    effective_at: datetime,
) -> tuple[CurrentEvidenceBasisQuery, CurrentEvidenceBasis, _DecisionStore]:
    query, key, target, _, _, store = _query(
        decision=_future_withdrawn_decision(effective_at=effective_at),
        histories=EvidenceHistories((), (), ()),
        empty=True,
    )
    _enroll_temporal_target(query, target)
    return query, _complete_current(query, key), store


def _invalidate_future_decision_fact(store: _DecisionStore) -> None:
    initiation, future = store.decision.history
    store.history_override = (
        initiation,
        replace(
            future,
            metadata=replace(future.metadata, fact_id=initiation.metadata.fact_id),
        ),
    )


def test_atomic_revalidation_reconstructs_prior_and_fresh_before_acceptance() -> None:
    query, key, prior = _empty_temporal_basis()
    participation = _AtomicParticipation(
        AtomicCurrentBasisRead(key, AT + timedelta(seconds=1), query)
    )

    result = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(prior, participation)
    )

    assert result is None
    assert participation.keys == [key]


def test_atomic_revalidation_rejects_old_read_instant() -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)

    result = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            prior, _AtomicParticipation(AtomicCurrentBasisRead(key, AT, query))
        )
    )

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_atomic_revalidation_detects_same_version_future_decision_change() -> None:
    later = AT + timedelta(seconds=1)
    query, prior, _ = _future_decision_temporal_basis(later)

    result = _revalidate_at(query, prior, later)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {StaleEvidenceBasisCategory.DECISION_CHANGED}
    assert result.changed_owner_meanings[0].prior is prior.owner_meaning.decision
    assert result.changed_owner_meanings[0].fresh.read_at == later


def test_atomic_revalidation_rejects_nonoperative_same_version_decision() -> None:
    later = AT + timedelta(seconds=1)
    decision, _, reader, *_ = _future_relationship_owner(effective_at=later)
    # duplicate-code: this command-bound fixture separately proves the classifier's
    # relationship
    # case through the complete owner query and atomic participation port.
    # arid: disable
    query, key, target, *_ = _query(
        decision=decision,
        histories=EvidenceHistories((), (), ()),
        empty=True,
    )
    query._decisions = DecisionMemoryService(reader=reader)
    query._decision_meaning = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))
    # arid: enable
    _enroll_temporal_target(query, target)
    prior = _complete_current(query, key)

    result = _revalidate_at(query, prior, later)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {StaleEvidenceBasisCategory.DECISION_CHANGED}
    assert result.changed_owner_meanings[0].fresh.meaning.applicability is (
        DecisionApplicability.NON_OPERATIVE
    )


def test_atomic_revalidation_accepts_equal_future_only_owner_meaning() -> None:
    query, _, prior = _empty_temporal_basis()
    query._target_meaning._owner.future_fact_at = AT + timedelta(days=1)
    prior = _complete_current(query, prior.key)

    assert _revalidate_at(query, prior, AT + timedelta(seconds=1)) is None


def test_atomic_revalidation_rejects_invalid_future_only_history() -> None:
    later = AT + timedelta(seconds=1)
    query, prior, store = _future_decision_temporal_basis(AT + timedelta(days=1))
    _invalidate_future_decision_fact(store)

    result = _revalidate_at(query, prior, later)

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_atomic_revalidation_rejects_contradictory_owner_meaning() -> None:
    query, _, prior = _empty_temporal_basis()
    owner = query._target_meaning._owner
    owner.failure = OwnerMeaningNoBasisReason.CONTRADICTORY
    owner.failure_for = TargetJudgmentMeaning

    result = _revalidate_at(query, prior, AT + timedelta(seconds=1))

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_atomic_revalidation_rejects_missing_write_participation() -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)

    result = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(prior, _AtomicParticipation(None))
    )

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.UNAVAILABLE


def test_atomic_revalidation_keeps_owner_participation_unavailable_distinct() -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)

    result = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(prior, _UnavailableParticipation())
    )

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.UNAVAILABLE
    assert "target owner" in result.detail


def test_atomic_revalidation_rejects_changed_prior_owner_history() -> None:
    query, key, target, *_ = _query()
    prior = _complete_current(query, key)
    owner, _ = _expected_target_proof(query, key, target)
    owner.meaning_at[prior.owner_meaning.target.subject] = (AT, "contradicted")

    result = asyncio.run(
        CurrentEvidenceBasisRevalidator().revalidate(
            prior,
            _AtomicParticipation(
                AtomicCurrentBasisRead(key, AT + timedelta(seconds=1), query)
            ),
        )
    )

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_atomic_revalidation_rejects_support_epoch_drift_after_prior_proof() -> None:
    query, key, target, _, epochs, _ = _empty_query(requirement_key())
    _enroll_temporal_target(query, target)
    prior = _complete_current(query, key)
    fresh_version = EvidenceSupportVersion(prior.support_version.value + 1)
    epochs.version = fresh_version
    query._sufficiency.version = fresh_version
    fresh = _complete_current(query, key, at=AT + timedelta(seconds=1))
    reads = _RevalidationReads(prior, fresh)

    result = _revalidate_scripted(prior, reads)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
    assert reads.reads == [AT, AT + timedelta(seconds=1)]
    assert reads.verified == [prior, fresh]


def test_atomic_revalidation_rejects_contradicted_prior_evidence_history() -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)
    other_epoch = EvidenceSupportVersion(prior.support_version.value + 1)
    reconstructed = replace(
        prior,
        support_version=other_epoch,
        sufficiency=replace(prior.sufficiency, support_version=other_epoch),
    )
    reads = _RevalidationReads(reconstructed, prior)

    result = _revalidate_scripted(prior, reads)

    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY
    assert reads.reads == [AT]
    assert reads.verified == [prior]


@pytest.mark.parametrize(
    "reason",
    [
        CurrentNoBasisReason.MISSING,
        CurrentNoBasisReason.INCOMPLETE,
        CurrentNoBasisReason.CONTESTED,
        CurrentNoBasisReason.NOT_YET_EFFECTIVE,
        CurrentNoBasisReason.INVALID_HISTORY,
        CurrentNoBasisReason.UNAVAILABLE,
    ],
)
def test_atomic_revalidation_preserves_fresh_no_basis_reason(
    reason: CurrentNoBasisReason,
) -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)
    fresh = CurrentEvidenceNoBasis(key, AT + timedelta(seconds=1), reason, "owner read")
    reads = _RevalidationReads(prior, fresh)

    result = _revalidate_scripted(prior, reads)

    assert result is fresh
    assert reads.verified == [prior]


def _read_later(
    query: CurrentEvidenceBasisQuery,
    key: BasisScopeKey,
    target: _Targets,
    later: datetime,
) -> CurrentEvidenceBasis:
    assert isinstance(target.result, ResolvedTargetJudgment)
    target.result = replace(target.result, effective_at=later, known_at=later)
    return _complete_current(query, key, at=later)


def _claim_scope(
    version: int,
) -> tuple[EvidenceRequirementApplicabilityKey, ResolvedClaimMembership]:
    claim_id = ClaimId(uuid4())
    application_key = replace(
        requirement_key(), scope=ClaimSpecificEvidenceScope(claim_id)
    )
    return application_key, ResolvedClaimMembership(
        application_key.target, claim_id, ClaimCatalogVersion(version)
    )


def _selected_alternative() -> SelectedContextFact:
    return SelectedContextFact(
        DecisionAlternativeVersionRef(
            DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
        ),
        "fact",
        "lineage",
        "applicable",
        "source",
        frozenset({ContextContribution.RESULT}),
    )


def _empty_query(
    application_key: EvidenceRequirementApplicabilityKey,
    *,
    claim_result: ResolvedClaimMembership | None = None,
    target_version: TargetJudgmentVersionRef | None = None,
) -> tuple[
    CurrentEvidenceBasisQuery,
    BasisScopeKey,
    _Targets,
    _Contexts,
    _Epochs,
    _DecisionStore,
]:
    return _query(
        applicability_key=application_key,
        histories=EvidenceHistories((), (), ()),
        empty=True,
        claim_result=claim_result,
        target_version=target_version,
    )


def _expected_target_proof(
    query: CurrentEvidenceBasisQuery, key: BasisScopeKey, target: _Targets
) -> tuple[_MeaningOwner, OwnerMeaningWitness]:
    owner = query._target_meaning._owner
    assert isinstance(target.result, ResolvedTargetJudgment)
    subject = TargetJudgmentMeaning(target.result.version)
    return owner, owner._expected(key, subject, AT)


def test_current_basis_captures_exact_owner_and_evidence_dependencies() -> None:
    query, key, target, contexts, epochs, decisions = _query()
    result = asyncio.run(query.read(key, at=AT))

    assert isinstance(result, CurrentEvidenceBasis)
    assert result.key == key and result.at == AT
    assert result.decision.version.value == 1
    assert isinstance(target.result, ResolvedTargetJudgment)
    assert result.target.version == target.result.version
    assert result.requirement_key == requirement_key()
    assert result.sufficiency.requirement_version == requirement_version()
    assert result.support_version == EvidenceSupportVersion(1)
    assert result.evidence.bindings[0].root == interpreted_binding().binding
    assert result.evidence.observations[0].root.source.source_identity == "provider"
    assert result.guards.binding_ids == frozenset(
        {interpreted_binding().binding.binding_id}
    )
    assert result.guards.assessment_ids == frozenset()
    assert result.context.guards == tuple(
        selection.guard for selection in result.context.selections
    )
    assert result.owner_meaning.decision.key == key
    assert result.owner_meaning.decision.read_at == AT
    assert result.owner_meaning.decision.cause.complete
    assert result.owner_meaning.decision.cause.fact_ancestry
    assert result.owner_meaning.decision.cause.relationship_guards
    assert result.owner_meaning.target.subject == TargetJudgmentMeaning(
        result.target.version
    )
    assert result.owner_meaning.claim is None
    assert tuple(proof.subject for proof in result.owner_meaning.context) == tuple(
        CanonicalContextAbsence(selection.role, selection.guard)
        for selection in result.context.selections
    )
    assert decisions.at == AT
    assert target.received == (key.target, AT, AT)
    assert len(contexts.calls) == len(ContextSelectionRole)
    assert all(call[2:] == (AT, AT) for call in contexts.calls)
    assert epochs.calls == [(key.target, key.scope, key.use, AT, AT)]


def test_two_decisions_consume_same_target_scope_use_epoch() -> None:
    first, first_key, *_ = _query()
    second, second_key, *_ = _query()
    first_basis = asyncio.run(first.read(first_key, at=AT))
    second_basis = asyncio.run(second.read(second_key, at=AT))

    assert isinstance(first_basis, CurrentEvidenceBasis)
    assert isinstance(second_basis, CurrentEvidenceBasis)
    assert first_key != second_key
    assert first_basis.support_version == second_basis.support_version
    assert first_basis.decision.decision_id != second_basis.decision.decision_id


@pytest.mark.parametrize(
    ("family", "version_type"),
    [
        (EvidenceJudgmentFamily.INVESTMENT_HYPOTHESIS, InvestmentHypothesisVersionRef),
        (EvidenceJudgmentFamily.INVESTMENT_VIEW, InvestmentViewVersionRef),
        (
            EvidenceJudgmentFamily.MEANINGFUL_CHALLENGE_RESULT,
            MeaningfulChallengeResultVersionRef,
        ),
        (
            EvidenceJudgmentFamily.PROJECTED_PORTFOLIO_CONSEQUENCE,
            ProjectedPortfolioConsequenceVersionRef,
        ),
        (
            EvidenceJudgmentFamily.PORTFOLIO_RISK_ASSESSMENT,
            PortfolioRiskAssessmentVersionRef,
        ),
        (
            EvidenceJudgmentFamily.INVESTMENT_RECOMMENDATION,
            InvestmentRecommendationVersionRef,
        ),
        (
            EvidenceJudgmentFamily.RECOMMENDATION_WITHHOLDING_JUDGMENT,
            RecommendationWithholdingJudgmentVersionRef,
        ),
        (
            EvidenceJudgmentFamily.HUMAN_INVESTMENT_DECISION,
            HumanInvestmentDecisionVersionRef,
        ),
        (EvidenceJudgmentFamily.DECISION_EVALUATION, DecisionEvaluationVersionRef),
        (EvidenceJudgmentFamily.LESSON, LessonVersionRef),
    ],
)
def test_every_target_owner_family_can_issue_current_basis(
    family: EvidenceJudgmentFamily, version_type: type
) -> None:
    target = evidence_judgment_ref(family, uuid4())
    application_key = replace(requirement_key(), target=target)
    version = version_type(target, JudgmentRevision(1))
    query, key, *_ = _empty_query(application_key, target_version=version)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.target.version == version
    assert result.owner_meaning.target.subject == TargetJudgmentMeaning(version)


def test_context_revision_and_selection_capture_without_epoch_change() -> None:
    query, key, _, contexts, _, _ = _query()
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    root = DecisionAlternativeId(uuid4())
    contexts.selected[role] = (
        SelectedContextFact(
            DecisionAlternativeVersionRef(root, DecisionAlternativeRevision(1)),
            "alternative",
            "root lineage",
            "applicable",
            "source",
            frozenset({ContextContribution.RESULT}),
        ),
    )
    before = asyncio.run(query.read(key, at=AT))
    contexts.selected[role] = (
        SelectedContextFact(
            DecisionAlternativeVersionRef(root, DecisionAlternativeRevision(2)),
            "corrected alternative",
            "root lineage",
            "applicable",
            "new source",
            frozenset({ContextContribution.RESULT}),
        ),
    )
    after = asyncio.run(query.read(key, at=AT))

    assert isinstance(before, CurrentEvidenceBasis)
    assert isinstance(after, CurrentEvidenceBasis)
    assert before.support_version == after.support_version
    assert before.context.positive_references != after.context.positive_references
    assert before.context.guards == after.context.guards

    replacement = DecisionAlternativeId(uuid4())
    contexts.selected[role] = (
        SelectedContextFact(
            DecisionAlternativeVersionRef(replacement, DecisionAlternativeRevision(1)),
            "replacement",
            "new root",
            "applicable",
            "source",
            frozenset({ContextContribution.RESULT}),
        ),
    )
    selected = asyncio.run(query.read(key, at=AT))
    assert isinstance(selected, CurrentEvidenceBasis)
    assert before.context.guards != selected.context.guards
    assert before.support_version == selected.support_version


@pytest.mark.parametrize(("role", "reference"), _OWNER_FAMILY_CASES)
def test_every_typed_context_family_enters_current_basis(
    role: ContextSelectionRole, reference: CanonicalContextVersionRef
) -> None:
    query, key, _, contexts, _, _ = _query()
    contexts.selected[role] = (
        SelectedContextFact(
            reference,
            "owner fact",
            "lineage",
            "applicability",
            "provenance",
            frozenset({ContextContribution.SUPPORT}),
        ),
    )
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert reference in result.context.positive_references
    assert result.context.guards[tuple(ContextSelectionRole).index(role)].selected == (
        frozenset({context_root(reference)})
    )
    assert any(
        proof.subject == CanonicalContextMeaning(role, reference, selection.guard)
        and proof.meaning == selection.facts[0]
        for selection in result.context.selections
        for proof in result.owner_meaning.context
        if selection.role is role
    )


def test_unavailable_target_returns_typed_no_basis() -> None:
    query, key, target, _, _, _ = _query()
    target.result = TargetJudgmentUnavailable(key.target, "owner offline")
    result = asyncio.run(query.read(key, at=AT))
    assert result == CurrentEvidenceNoBasis(
        key, AT, CurrentNoBasisReason.UNAVAILABLE, "owner offline"
    )


@pytest.mark.parametrize(
    ("owner_reason", "expected"),
    [
        (ContextNoBasisReason.MISSING_REQUIRED, CurrentNoBasisReason.MISSING),
        (
            ContextNoBasisReason.INCOMPLETE_MEMBERSHIP,
            CurrentNoBasisReason.INCOMPLETE,
        ),
        (ContextNoBasisReason.CONTESTED, CurrentNoBasisReason.CONTESTED),
        (
            ContextNoBasisReason.INVALID_HISTORY,
            CurrentNoBasisReason.INVALID_HISTORY,
        ),
        (
            ContextNoBasisReason.UNAVAILABLE_AUTHORITY,
            CurrentNoBasisReason.UNAVAILABLE,
        ),
    ],
)
def test_incomplete_or_failed_context_cannot_produce_basis(
    owner_reason: ContextNoBasisReason, expected: CurrentNoBasisReason
) -> None:
    query, key, _, contexts, _, _ = _query()
    contexts.failure = owner_reason
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is expected


def test_claim_specific_basis_carries_separate_catalog_membership_guard() -> None:
    application_key, membership = _claim_scope(3)
    query, key, *_ = _empty_query(application_key, claim_result=membership)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.claim_catalog_version == ClaimCatalogVersion(3)
    assert result.guards.claim is not None
    assert result.guards.claim.membership == membership
    assert result.owner_meaning.claim is not None
    assert result.owner_meaning.claim.subject == ClaimMembershipMeaning(
        key.target, membership.claim_id, membership.catalog_version
    )


def test_claim_catalog_change_is_separate_from_target_revision_and_epoch() -> None:
    decision = _decision()
    claim_id = ClaimId(uuid4())
    application_key = replace(
        requirement_key(), scope=ClaimSpecificEvidenceScope(claim_id)
    )
    empty = EvidenceHistories((), (), ())
    first_query, first_key, *_ = _query(
        decision=decision,
        applicability_key=application_key,
        histories=empty,
        empty=True,
        claim_result=ResolvedClaimMembership(
            application_key.target, claim_id, ClaimCatalogVersion(1)
        ),
    )
    # duplicate-code: the second claim-catalog candidate repeats setup deliberately so
    # only its owner
    # version changes.
    # arid: disable
    second_query, second_key, *_ = _query(
        decision=decision,
        applicability_key=application_key,
        histories=empty,
        empty=True,
        claim_result=ResolvedClaimMembership(
            application_key.target, claim_id, ClaimCatalogVersion(2)
        ),
    )
    before = asyncio.run(first_query.read(first_key, at=AT))
    after = asyncio.run(second_query.read(second_key, at=AT))
    assert isinstance(before, CurrentEvidenceBasis)
    assert isinstance(after, CurrentEvidenceBasis)
    assert before.key == after.key
    # arid: enable
    assert before.target.version == after.target.version
    assert before.support_version == after.support_version
    assert before.claim_catalog_version != after.claim_catalog_version


def test_requirement_change_is_separate_from_evidence_epoch() -> None:
    decision = _decision()
    empty = EvidenceHistories((), (), ())
    first_query, first_key, *_ = _query(
        decision=decision,
        histories=empty,
        empty=True,
        version=EvidenceSupportVersion(0),
    )
    # duplicate-code: the second requirement candidate repeats setup deliberately so
    # only requirement
    # authority changes.
    # arid: disable
    second_query, second_key, *_ = _query(
        decision=decision,
        histories=empty,
        empty=True,
        version=EvidenceSupportVersion(0),
    )
    second_query._sufficiency.authority_override = requirement_version(
        # arid: enable
        SECOND_VERSION_ID
    )
    before = asyncio.run(first_query.read(first_key, at=AT))
    after = asyncio.run(second_query.read(second_key, at=AT))
    assert isinstance(before, CurrentEvidenceBasis)
    assert isinstance(after, CurrentEvidenceBasis)
    assert before.key == after.key
    assert before.support_version == after.support_version
    assert before.sufficiency.requirement_version.version_id != (
        after.sufficiency.requirement_version.version_id
    )


def test_scope_epoch_mismatch_fails_closed() -> None:
    query, key, _, _, epochs, _ = _query()
    epochs.version = EvidenceSupportVersion(2)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INCOMPLETE


def test_support_only_epoch_change_is_consumed_with_same_facts() -> None:
    before_query, before_key, *_ = _query(version=EvidenceSupportVersion(1))
    after_query, after_key, *_ = _query(version=EvidenceSupportVersion(2))
    before = asyncio.run(before_query.read(before_key, at=AT))
    after = asyncio.run(after_query.read(after_key, at=AT))
    assert isinstance(before, CurrentEvidenceBasis)
    assert isinstance(after, CurrentEvidenceBasis)
    assert before.evaluation == after.evaluation
    assert before.support_version != after.support_version


def test_empty_scope_consumes_zero_epoch_without_inventing_support() -> None:
    query, key, *_ = _query(
        histories=EvidenceHistories((), (), ()),
        version=EvidenceSupportVersion(0),
        empty=True,
    )
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.support_version == EvidenceSupportVersion(0)
    assert result.guards.binding_ids == frozenset()
    assert result.evidence.observations == ()


def test_late_recorded_observation_correction_changes_current_fact_support() -> None:
    histories = _histories()
    observation = histories.observations[0].root
    correction = EvidenceObservationCorrection(
        EvidenceCorrectionId(uuid4()),
        observation.observation_id,
        observation.observation_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("provider corrected source"),
        observation.effective_at,
        AT + timedelta(minutes=1),
        replace(
            observation,
            material=EvidenceObservationMaterial(retained_representation="101"),
        ),
    )
    histories = replace(
        histories,
        observations=(replace(histories.observations[0], corrections=(correction,)),),
    )
    before_query, before_key, *_ = _query(histories=histories)
    before = asyncio.run(before_query.read(before_key, at=AT))
    assert isinstance(before, CurrentEvidenceBasis)
    assert correction.correction_id not in before.guards.fact_support

    later = AT + timedelta(minutes=2)
    after_query, after_key, owner, *_ = _query(
        histories=histories, version=EvidenceSupportVersion(2)
    )
    assert isinstance(owner.result, ResolvedTargetJudgment)
    owner.result = replace(owner.result, effective_at=later, known_at=later)
    original = interpreted_binding()
    after_query._sufficiency.interpretations_override = (
        replace(
            original,
            fact_support=original.fact_support | frozenset({correction.correction_id}),
        ),
    )
    after = asyncio.run(after_query.read(after_key, at=later))
    assert isinstance(after, CurrentEvidenceBasis)
    assert correction.correction_id in after.guards.fact_support
    assert after.evidence.observations[0].interpretation.assertions == frozenset(
        {correction.replacement}
    )


def test_binding_correction_support_is_kept_with_exact_key() -> None:
    histories = _histories()
    binding = histories.bindings[0].root
    revised = replace(binding, role=EvidenceRole.QUALIFYING)
    # duplicate-code: this binding correction is constructed locally to prove current
    # support and
    # provenance capture.
    # arid: disable
    correction = EvidenceBindingCorrection(
        EvidenceCorrectionId(uuid4()),
        binding.binding_id,
        binding.binding_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("role correction"),
        binding.effective_at,
        AT + timedelta(minutes=1),
        revised,
    )
    histories = replace(
        # arid: enable
        histories,
        bindings=(replace(histories.bindings[0], corrections=(correction,)),),
    )
    later = AT + timedelta(minutes=2)
    query, key, owner, *_ = _query(
        histories=histories, version=EvidenceSupportVersion(2)
    )
    assert isinstance(owner.result, ResolvedTargetJudgment)
    owner.result = replace(owner.result, effective_at=later, known_at=later)
    interpreted = interpreted_binding()
    query._sufficiency.interpretations_override = (
        replace(
            interpreted,
            binding=revised,
            surviving_bindings=frozenset({revised}),
            fact_support=interpreted.fact_support
            | frozenset({correction.correction_id}),
        ),
    )
    result = asyncio.run(query.read(key, at=later))
    assert isinstance(result, CurrentEvidenceBasis)
    assert correction.correction_id in result.guards.fact_support
    assert result.evidence.bindings[0].interpretation.assertions == frozenset({revised})


def test_corrected_binding_applicability_enters_current_basis() -> None:
    histories = _histories()
    binding = histories.bindings[0].root
    corrected_key = replace(
        requirement_key(), investment_horizon=InvestmentHorizon("ten trading days")
    )
    # duplicate-code: the applicability revision stays explicit here so this
    # owner-query falsifier does not inherit its expected key from the DB proof.
    # arid: disable
    revised = replace(
        binding,
        freshness=replace(
            binding.freshness,
            basis=replace(binding.freshness.basis, applicability_key=corrected_key),
        ),
    )
    correction = EvidenceBindingCorrection(
        EvidenceCorrectionId(uuid4()),
        binding.binding_id,
        binding.binding_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("correct applicability"),
        binding.effective_at,
        AT - timedelta(minutes=1),
        revised,
    )
    # arid: enable
    histories = replace(
        histories,
        bindings=(replace(histories.bindings[0], corrections=(correction,)),),
    )
    query, key, *_ = _query(histories=histories, applicability_key=corrected_key)
    # duplicate-code: this owner reply independently exposes the corrected
    # applicability in the application coherence check.
    # arid: disable
    interpreted = interpreted_binding()
    query._sufficiency.interpretations_override = (
        replace(
            interpreted,
            binding=revised,
            surviving_bindings=frozenset({revised}),
            fact_support=interpreted.fact_support
            | frozenset({correction.correction_id}),
        ),
    )
    # arid: enable
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.evidence.bindings[0].interpretation.assertions == frozenset({revised})
    assert result.guards.binding_ids == frozenset({binding.binding_id})


def test_binding_restoration_and_competing_corrections_are_distinguished() -> None:
    histories = _histories()
    binding = histories.bindings[0].root
    # duplicate-code: this restoration falsifier constructs its own correction branch
    # independently of
    # the single-correction proof.
    # arid: disable
    first = EvidenceBindingCorrection(
        EvidenceCorrectionId(uuid4()),
        binding.binding_id,
        binding.binding_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("first review"),
        binding.effective_at,
        AT + timedelta(minutes=1),
        replace(binding, role=EvidenceRole.QUALIFYING),
    )
    restore = EvidenceBindingCorrection(
        # arid: enable
        EvidenceCorrectionId(uuid4()),
        binding.binding_id,
        first.correction_id,
        EvidenceCorrectionEffect.RETRACT,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("restore prior assertion"),
        binding.effective_at,
        AT + timedelta(minutes=2),
    )
    later = AT + timedelta(minutes=3)
    restored_history = replace(
        histories,
        bindings=(replace(histories.bindings[0], corrections=(first, restore)),),
    )
    # duplicate-code: this restoration candidate repeats exact owner setup so the
    # changed correction
    # ancestry is isolated.
    # arid: disable
    query, key, owner, *_ = _query(
        histories=restored_history, version=EvidenceSupportVersion(3)
    )
    assert isinstance(owner.result, ResolvedTargetJudgment)
    owner.result = replace(owner.result, effective_at=later, known_at=later)
    interpreted = interpreted_binding()
    query._sufficiency.interpretations_override = (
        replace(
            interpreted,
            fact_support=interpreted.fact_support
            | frozenset({first.correction_id, restore.correction_id}),
        ),
    )
    # arid: enable
    result = asyncio.run(query.read(key, at=later))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.evidence.bindings[0].interpretation.state is (
        EvidenceInterpretationState.DETERMINATE
    )
    assert result.evidence.bindings[0].interpretation.assertions == frozenset({binding})

    competing = replace(
        restore,
        target=binding.binding_id,
        effect=EvidenceCorrectionEffect.REVISE,
        replacement=replace(binding, role=EvidenceRole.CONFLICTING),
    )
    query._evidence.histories = replace(
        histories,
        bindings=(replace(histories.bindings[0], corrections=(first, competing)),),
    )
    contested = asyncio.run(query.read(key, at=later))
    assert isinstance(contested, CurrentEvidenceNoBasis)
    assert contested.reason is CurrentNoBasisReason.CONTESTED


def test_assessment_retraction_retains_ancestry_but_clears_current_selection() -> None:
    assessment = derived_assessment()
    correction = EvidenceAssessmentCorrection(
        EvidenceCorrectionId(uuid4()),
        assessment.assessment_id,
        assessment.assessment_id,
        EvidenceCorrectionEffect.RETRACT,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("assessment retracted"),
        AT,
        AT + timedelta(minutes=1),
    )
    # duplicate-code: this assessment-retraction candidate repeats exact owner setup to
    # isolate the new
    # correction branch.
    # arid: disable
    histories = replace(
        _histories(),
        assessments=(EvidenceAssessmentCorrectionHistory(assessment, (correction,)),),
    )
    later = AT + timedelta(minutes=2)
    query, key, owner, *_ = _query(
        histories=histories, version=EvidenceSupportVersion(2)
    )
    assert isinstance(owner.result, ResolvedTargetJudgment)
    owner.result = replace(owner.result, effective_at=later, known_at=later)
    result = asyncio.run(query.read(key, at=later))
    # arid: enable
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.evidence.current_assessments == ()
    assert correction.correction_id in result.guards.fact_support


def test_time_only_fitness_changes_with_stable_owner_versions_and_epoch() -> None:
    query, key, owner, *_ = _query()
    before = asyncio.run(query.read(key, at=AT))
    later = AT + timedelta(days=1)
    assert isinstance(owner.result, ResolvedTargetJudgment)
    owner.result = replace(owner.result, effective_at=later, known_at=later)
    after = asyncio.run(query.read(key, at=later))
    assert isinstance(before, CurrentEvidenceBasis)
    assert isinstance(after, CurrentEvidenceBasis)
    assert before.decision.version == after.decision.version
    assert before.target.version == after.target.version
    assert before.support_version == after.support_version
    assert before.evaluation.result != after.evaluation.result


def test_current_reassessment_selection_and_absence_guard() -> None:
    histories = _histories()
    first = derived_assessment()
    second = replace(
        derived_assessment(2), reassesses_assessment_id=first.assessment_id
    )
    histories = replace(
        histories,
        assessments=(
            EvidenceAssessmentCorrectionHistory(first, ()),
            EvidenceAssessmentCorrectionHistory(second, ()),
        ),
    )
    query, key, *_ = _query(histories=histories)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.guards.assessment_ids == frozenset(
        {first.assessment_id, second.assessment_id}
    )
    assert tuple(
        item.root.assessment_id for item in result.evidence.current_assessments
    ) == (second.assessment_id,)


def test_competing_assessment_roots_return_typed_no_basis() -> None:
    histories = replace(
        _histories(),
        assessments=(
            EvidenceAssessmentCorrectionHistory(derived_assessment(), ()),
            EvidenceAssessmentCorrectionHistory(derived_assessment(2), ()),
        ),
    )
    query, key, *_ = _query(histories=histories)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.CONTESTED


def test_missing_requirement_authority_fails_closed() -> None:
    query, key, *_ = _query()
    query._sufficiency.result = MissingEvidenceRequirementAuthority()
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.MISSING


def test_assessment_requires_its_historical_requirement_version() -> None:
    histories = replace(
        _histories(),
        assessments=(EvidenceAssessmentCorrectionHistory(derived_assessment(), ()),),
    )
    query, key, *_ = _query(histories=histories)

    class ChangedHistoricalRequirements:
        async def resolve(
            self,
            key: EvidenceRequirementApplicabilityKey,
            *,
            effective_at: datetime,
            known_at: datetime,
        ) -> ResolvedEvidenceRequirementVersion:
            return ResolvedEvidenceRequirementVersion(
                requirement_version(SECOND_VERSION_ID)
            )

    query._requirements = ChangedHistoricalRequirements()
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_missing_observation_fails_closed_only_for_selected_scope() -> None:
    histories = _histories()
    query, key, *_ = _query(histories=EvidenceHistories((), histories.bindings, ()))
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INCOMPLETE


def test_invalid_scoped_history_returns_typed_no_basis() -> None:
    query, key, *_ = _query()

    async def invalid_history(key: BasisScopeKey, *, at: datetime) -> EvidenceHistories:
        raise EvidenceHistoryInvalid("selected correction ancestry is invalid")

    query._evidence.load_scope_histories = invalid_history
    # duplicate-code: This assertion independently proves the scoped history
    # failure path; sharing the historical requirement falsifier would couple
    # two different owner-failure boundaries.
    # arid: disable
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY
    # arid: enable


def test_future_and_other_scope_histories_do_not_enter_current_basis() -> None:
    histories = _histories()
    unrelated = interpreted_binding(2).binding
    other_key = replace(requirement_key(), evidence_use=EvidenceUse.CHALLENGE_BASIS)
    unrelated = replace(
        unrelated,
        evidence_use=EvidenceUse.CHALLENGE_BASIS,
        freshness=replace(
            unrelated.freshness,
            basis=replace(unrelated.freshness.basis, applicability_key=other_key),
        ),
    )
    future = replace(
        interpreted_binding(3).binding,
        effective_at=AT + timedelta(days=1),
        recorded_at=AT - timedelta(minutes=1),
    )
    changed = EvidenceHistories(
        histories.observations,
        histories.bindings
        + (
            EvidenceBindingCorrectionHistory(unrelated, ()),
            EvidenceBindingCorrectionHistory(future, ()),
        ),
        (),
    )
    query, key, *_ = _query(histories=changed)
    result = asyncio.run(query.read(key, at=AT))

    assert isinstance(result, CurrentEvidenceBasis)
    assert len(result.evidence.bindings) == 1
    assert result.guards.binding_ids == frozenset(
        {interpreted_binding().binding.binding_id}
    )


def test_unaware_current_instant_is_rejected() -> None:
    query, key, *_ = _query()
    with pytest.raises(ValueError, match="timezone-aware"):
        asyncio.run(query.read(key, at=datetime(2026, 9, 29)))


def _future_withdrawn_decision(
    *,
    effective_at: datetime | None = None,
) -> InvestmentDecision:
    decision = _decision()
    metadata = decision.history[0].metadata
    return withdraw_decision_work(
        decision,
        basis=DecisionWorkControlBasis("future withdrawal"),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            OperationId(uuid4()),
            metadata.actor_attribution,
            metadata.trigger,
            effective_at or AT + timedelta(days=1),
            AT - timedelta(minutes=1),
            metadata.technical_provenance,
        ),
    )


def test_current_basis_retains_distinct_concrete_decision_temporal_witness() -> None:
    query, key, target, _, _, _ = _query(decision=_future_withdrawn_decision())
    prior = _complete_current(query, key)
    later = AT + timedelta(days=1)
    fresh = _read_later(query, key, target, later)

    assert prior.decision.version == fresh.decision.version
    assert prior.owner_meaning.decision.subject == fresh.owner_meaning.decision.subject
    assert (
        prior.owner_meaning.decision.meaning.work_posture is DecisionWorkPosture.ACTIVE
    )
    assert fresh.owner_meaning.decision.meaning.work_posture is (
        DecisionWorkPosture.WITHDRAWN
    )
    assert (
        prior.owner_meaning.decision.semantic_identity
        != fresh.owner_meaning.decision.semantic_identity
    )
    assert prior.owner_meaning.decision.cause == fresh.owner_meaning.decision.cause


def test_future_only_owner_history_is_retained_without_material_change() -> None:
    query, key, target, *_ = _query()
    owner = query._target_meaning._owner
    owner.future_fact_at = AT + timedelta(days=1)
    prior = _complete_current(query, key)
    later = AT + timedelta(hours=1)
    fresh = _read_later(query, key, target, later)

    assert len(prior.owner_meaning.target.cause.fact_ancestry) == 2
    assert prior.owner_meaning.target.cause.fact_ancestry[1].effective_at > AT
    assert prior.owner_meaning.target.cause == fresh.owner_meaning.target.cause
    assert (
        prior.owner_meaning.target.semantic_identity
        == fresh.owner_meaning.target.semantic_identity
    )


def test_downstream_owner_meaning_changes_without_reference_or_version_change() -> None:
    application_key, membership = _claim_scope(1)
    query, key, target, contexts, _, _ = _empty_query(
        application_key, claim_result=membership
    )
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    selected = _selected_alternative()
    contexts.selected[role] = (selected,)
    prior = _complete_current(query, key)
    later = AT + timedelta(days=1)
    owner = query._target_meaning._owner
    owner.future_fact_at = later
    owner.meaning_at[prior.owner_meaning.target.subject] = (
        later,
        "target now operative",
    )
    assert prior.owner_meaning.claim is not None
    owner.meaning_at[prior.owner_meaning.claim.subject] = (later, "claim now qualified")
    selected_proof = next(
        proof
        for proof in prior.owner_meaning.context
        if isinstance(proof.subject, CanonicalContextMeaning)
    )
    owner.meaning_at[selected_proof.subject] = (later, "context now operative")
    fresh = _read_later(query, key, target, later)

    assert prior.target.version == fresh.target.version
    assert prior.claim_catalog_version == fresh.claim_catalog_version
    assert prior.context.positive_references == fresh.context.positive_references
    assert prior.context.guards == fresh.context.guards
    assert (
        prior.owner_meaning.target.semantic_identity
        != fresh.owner_meaning.target.semantic_identity
    )
    assert fresh.owner_meaning.claim is not None
    assert (
        prior.owner_meaning.claim.semantic_identity
        != fresh.owner_meaning.claim.semantic_identity
    )
    fresh_context = next(
        proof
        for proof in fresh.owner_meaning.context
        if proof.subject == selected_proof.subject
    )
    assert selected_proof.semantic_identity != fresh_context.semantic_identity


def test_invalid_future_only_decision_history_cannot_produce_current_basis() -> None:
    query, key, _, _, _, store = _query(decision=_future_withdrawn_decision())
    _invalidate_future_decision_fact(store)
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_not_yet_effective_decision_has_distinct_no_basis_reason() -> None:
    query, key, _, _, _, store = _query()
    initiated = store.decision.history[0]
    store.history_override = (
        replace(
            initiated,
            metadata=replace(initiated.metadata, effective_at=AT + timedelta(days=1)),
        ),
    )
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.NOT_YET_EFFECTIVE


@pytest.mark.parametrize(
    ("owner_reason", "expected"),
    [
        (OwnerMeaningNoBasisReason.MISSING, CurrentNoBasisReason.MISSING),
        (OwnerMeaningNoBasisReason.INCOMPLETE, CurrentNoBasisReason.INCOMPLETE),
        (OwnerMeaningNoBasisReason.CONTESTED, CurrentNoBasisReason.CONTESTED),
        (
            OwnerMeaningNoBasisReason.NOT_YET_EFFECTIVE,
            CurrentNoBasisReason.NOT_YET_EFFECTIVE,
        ),
        (OwnerMeaningNoBasisReason.UNAVAILABLE, CurrentNoBasisReason.UNAVAILABLE),
        (
            OwnerMeaningNoBasisReason.CONTRADICTORY,
            CurrentNoBasisReason.INVALID_HISTORY,
        ),
        (
            OwnerMeaningNoBasisReason.INVALID_HISTORY,
            CurrentNoBasisReason.INVALID_HISTORY,
        ),
    ],
)
def test_target_owner_proof_failure_never_returns_partial_basis(
    owner_reason: OwnerMeaningNoBasisReason, expected: CurrentNoBasisReason
) -> None:
    query, key, *_ = _query()
    owner = query._target_meaning._owner
    owner.failure = owner_reason
    owner.failure_for = TargetJudgmentMeaning
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is expected


def test_mismatched_boundary_and_unverified_cause_reject_owner_proof() -> None:
    query, key, target, *_ = _query()
    owner, expected = _expected_target_proof(query, key, target)
    owner.override_for = TargetJudgmentMeaning
    owner.override = replace(expected, read_at=AT + timedelta(seconds=1))
    mismatch = asyncio.run(query.read(key, at=AT))
    assert isinstance(mismatch, CurrentEvidenceNoBasis)
    assert mismatch.reason is CurrentNoBasisReason.INVALID_HISTORY

    owner.override = replace(expected, meaning=("unsupported", ()))
    unsupported = asyncio.run(query.read(key, at=AT))
    assert isinstance(unsupported, CurrentEvidenceNoBasis)
    assert unsupported.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_mismatched_owner_version_and_context_selection_guard_fail_closed() -> None:
    query, key, target, contexts, *_ = _query()
    owner, expected = _expected_target_proof(query, key, target)
    owner.override_for = TargetJudgmentMeaning
    owner.override = replace(
        expected,
        subject=TargetJudgmentMeaning(
            InvestmentRecommendationVersionRef(key.target, JudgmentRevision(2))
        ),
    )
    version_failure = asyncio.run(query.read(key, at=AT))
    assert isinstance(version_failure, CurrentEvidenceNoBasis)
    assert version_failure.reason is CurrentNoBasisReason.INVALID_HISTORY

    owner.override = None
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    selected = _selected_alternative()
    contexts.selected[role] = (selected,)
    current = _complete_current(query, key)
    selected_proof = next(
        proof
        for proof in current.owner_meaning.context
        if isinstance(proof.subject, CanonicalContextMeaning)
    )
    contexts.revision += 1
    owner.override_for = CanonicalContextMeaning
    owner.override = selected_proof
    guard_failure = asyncio.run(query.read(key, at=AT))
    assert isinstance(guard_failure, CurrentEvidenceNoBasis)
    assert guard_failure.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_every_selected_context_fact_has_its_own_verified_witness() -> None:
    query, key, _, contexts, *_ = _query()
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    contexts.selected[role] = (_selected_alternative(), _selected_alternative())
    result = _complete_current(query, key)
    selected_proofs = tuple(
        proof
        for proof in result.owner_meaning.context
        if isinstance(proof.subject, CanonicalContextMeaning)
    )
    assert len(selected_proofs) == 2
    assert {proof.subject.reference for proof in selected_proofs} == set(
        result.context.positive_references
    )
    assert len(result.owner_meaning.context) == len(ContextSelectionRole) + 1


def test_context_and_claim_owner_proof_failure_keep_distinct_roles() -> None:
    query, key, *_ = _query()
    owner = query._context_meaning._owner
    owner.failure = OwnerMeaningNoBasisReason.INCOMPLETE
    owner.failure_for = CanonicalContextAbsence
    context_failure = asyncio.run(query.read(key, at=AT))
    assert isinstance(context_failure, CurrentEvidenceNoBasis)
    assert context_failure.reason is CurrentNoBasisReason.INCOMPLETE

    application_key, membership = _claim_scope(1)
    query, key, *_ = _empty_query(application_key, claim_result=membership)
    owner = query._claim_meaning._owner
    owner.failure = OwnerMeaningNoBasisReason.CONTESTED
    owner.failure_for = ClaimMembershipMeaning
    claim_failure = asyncio.run(query.read(key, at=AT))
    assert isinstance(claim_failure, CurrentEvidenceNoBasis)
    assert claim_failure.reason is CurrentNoBasisReason.CONTESTED
