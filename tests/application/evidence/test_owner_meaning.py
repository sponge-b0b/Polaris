from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.evidence.owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    ClaimMembershipMeaning,
    GoverningDecisionMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningReadUnavailable,
    OwnerMeaningResolver,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
    TargetJudgmentMeaning,
)
from polaris.domain.decisions.facts import DecisionVersion, InvestmentDecisionId
from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextRootRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
    DecisionContextVersionRef,
    InvestmentAuthorityRegimeId,
    InvestmentAuthorityRegimeRevision,
    InvestmentAuthorityRegimeVersionRef,
    InvestmentMandateId,
    InvestmentMandateRevision,
    InvestmentMandateVersionRef,
    InvestmentStrategyId,
    InvestmentStrategyRevision,
    InvestmentStrategyVersionRef,
    OtherJudgmentContextVersionRef,
    OutcomeId,
    OutcomeRevision,
    OutcomeVersionRef,
    PortfolioBoundaryId,
    PortfolioBoundaryRevision,
    PortfolioBoundaryVersionRef,
    PortfolioStateId,
    PortfolioStateRevision,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateId,
    ProjectedPortfolioStateRevision,
    ProjectedPortfolioStateVersionRef,
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
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    DecisionEvaluationRef,
    EvidenceJudgmentRef,
    EvidenceUse,
    HumanInvestmentDecisionRef,
    InvestmentHypothesisRef,
    InvestmentRecommendationRef,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
    LessonRef,
    MeaningfulChallengeResultRef,
    PortfolioRiskAssessmentRef,
    ProjectedPortfolioConsequenceRef,
    RecommendationWithholdingJudgmentRef,
)

_T0 = datetime(2026, 1, 1, tzinfo=UTC)
_T1 = _T0 + timedelta(days=1)
_T2 = _T0 + timedelta(days=2)


def _key(*, claim: ClaimId | None = None) -> BasisScopeKey:
    return BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        InvestmentViewRef(uuid4()),
        ClaimSpecificEvidenceScope(claim) if claim else JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )


def _decision_subject(key: BasisScopeKey) -> GoverningDecisionMeaning:
    return GoverningDecisionMeaning(
        DecisionContextVersionRef(key.decision_id, DecisionVersion(1))
    )


def _decision_setup() -> tuple[
    BasisScopeKey, GoverningDecisionMeaning, _OwnerDouble, OwnerMeaningResolver
]:
    key = _key()
    subject = _decision_subject(key)
    owner = _OwnerDouble()
    return key, subject, owner, OwnerMeaningResolver(owner)


def _lawful_pair(
    key: BasisScopeKey, subject: OwnerMeaningSubject
) -> tuple[
    _OwnerDouble, OwnerMeaningResolver, OwnerMeaningWitness, OwnerMeaningWitness
]:
    owner = _OwnerDouble()
    owner.records.append(_OwnerRecord(_T2, _T0, "after"))
    resolver = OwnerMeaningResolver(owner)
    prior = asyncio.run(resolver.read_current(key, subject, at=_T1))
    fresh = asyncio.run(resolver.read_current(key, subject, at=_T2))
    assert isinstance(prior, OwnerMeaningWitness)
    assert isinstance(fresh, OwnerMeaningWitness)
    assert prior.subject == fresh.subject
    assert prior.semantic_identity != fresh.semantic_identity
    return owner, resolver, prior, fresh


# duplicate-code: this owner-double relationship is independent from the
# current-basis double; sharing it would couple distinct contract proofs.
# arid: disable
@dataclass(frozen=True, slots=True)
class _SelectionUniverse:
    key: BasisScopeKey
    role: ContextSelectionRole


@dataclass(frozen=True, slots=True)
class _Relationship:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: ContextRootRef


# arid: enable


def _selected(
    key: BasisScopeKey, role: ContextSelectionRole, root: ContextRootRef
) -> ContextSelectionGuard:
    return ContextSelectionGuard(
        key,
        role,
        frozenset({root}),
        frozenset({_Relationship(key, role, root)}),
        _SelectionUniverse(key, role),
    )


@dataclass(frozen=True, slots=True)
class _OwnerRecord:
    effective_at: datetime
    recorded_at: datetime
    meaning: str
    provenance: str = "owner-source"


class _OwnerDouble:
    """Checks complete known history, including future-only facts, on every read."""

    def __init__(self) -> None:
        self.records = [_OwnerRecord(_T0, _T0, "before")]
        self.corrections: list[_OwnerRecord] = []
        self.override: OwnerMeaningWitness | OwnerMeaningNoBasis | None = None
        self.unavailable = False
        self.calls: list[tuple[BasisScopeKey, OwnerMeaningSubject, datetime]] = []

    def _expected(
        self, key: BasisScopeKey, subject: OwnerMeaningSubject, at: datetime
    ) -> OwnerMeaningWitness:
        known = [record for record in self.records if record.recorded_at <= at]
        active = max(
            (record for record in known if record.effective_at <= at),
            key=lambda record: record.effective_at,
        )
        guard = (
            subject.selection
            if isinstance(subject, (CanonicalContextMeaning, CanonicalContextAbsence))
            else subject
        )
        cause = OwnerMeaningCause(
            tuple(
                OwnerHistoryRecord(record, record.effective_at, record.recorded_at)
                for record in known
            ),
            tuple(
                OwnerHistoryRecord(
                    correction, correction.effective_at, correction.recorded_at
                )
                for correction in self.corrections
                if correction.recorded_at <= at
            ),
            (guard,),
            True,
        )
        return OwnerMeaningWitness(
            key, subject, at, at, at, active.meaning, active.provenance, cause
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
        self.calls.append((key, subject, read_at))
        if self.unavailable:
            raise OwnerMeaningReadUnavailable("owner offline")
        return self.override or self._expected(key, subject, read_at)

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        if self.unavailable:
            raise OwnerMeaningReadUnavailable("owner offline")
        known = [r for r in self.records if r.recorded_at <= validation_at]
        if len({r.effective_at for r in known}) != len(known):
            return OwnerMeaningNoBasisReason.CONTRADICTORY
        expected = self._expected(witness.key, witness.subject, witness.known_at)
        if witness == expected:
            return OwnerCauseVerdict.VALID
        if witness.cause != expected.cause:
            return OwnerMeaningNoBasisReason.INCOMPLETE
        return OwnerMeaningNoBasisReason.INVALID_HISTORY


# duplicate-code: the application owner-double matrix independently verifies
# all target variants; reusing domain test cases would create common-mode proof.
# arid: disable
_TARGET_PAIRS = (
    (InvestmentHypothesisRef, InvestmentHypothesisVersionRef),
    (InvestmentViewRef, InvestmentViewVersionRef),
    (MeaningfulChallengeResultRef, MeaningfulChallengeResultVersionRef),
    (ProjectedPortfolioConsequenceRef, ProjectedPortfolioConsequenceVersionRef),
    (PortfolioRiskAssessmentRef, PortfolioRiskAssessmentVersionRef),
    (InvestmentRecommendationRef, InvestmentRecommendationVersionRef),
    (RecommendationWithholdingJudgmentRef, RecommendationWithholdingJudgmentVersionRef),
    (HumanInvestmentDecisionRef, HumanInvestmentDecisionVersionRef),
    (DecisionEvaluationRef, DecisionEvaluationVersionRef),
    (LessonRef, LessonVersionRef),
)
# arid: enable


@pytest.mark.parametrize("root_type,version_type", _TARGET_PAIRS)
def test_every_typed_target_family_has_an_owner_verified_witness(
    root_type: type[EvidenceJudgmentRef],
    version_type: type,
) -> None:
    root = root_type(uuid4())
    key = BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        root,
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )
    subject = TargetJudgmentMeaning(version_type(root, JudgmentRevision(1)))
    owner = _OwnerDouble()
    result = asyncio.run(OwnerMeaningResolver(owner).read_current(key, subject, at=_T0))
    assert isinstance(result, OwnerMeaningWitness)
    assert result.subject.reference.root == root
    assert owner.calls == [(key, subject, _T0)]


def test_governing_decision_and_claim_membership_have_distinct_typed_subjects() -> None:
    claim = ClaimId(uuid4())
    key = _key(claim=claim)
    owner = _OwnerDouble()
    resolver = OwnerMeaningResolver(owner)
    decision = GoverningDecisionMeaning(
        DecisionContextVersionRef(key.decision_id, DecisionVersion(1))
    )
    membership = ClaimMembershipMeaning(key.target, claim, ClaimCatalogVersion(1))
    assert isinstance(
        asyncio.run(resolver.read_current(key, decision, at=_T0)), OwnerMeaningWitness
    )
    assert isinstance(
        asyncio.run(resolver.read_current(key, membership, at=_T0)), OwnerMeaningWitness
    )


def _context_cases(key: BasisScopeKey) -> tuple[CanonicalContextMeaning, ...]:
    prior_id = InvestmentDecisionId(uuid4())
    other = InvestmentHypothesisRef(uuid4())
    refs = (
        (
            ContextSelectionRole.USED_PRIOR_DECISION,
            DecisionContextVersionRef(prior_id, DecisionVersion(1)),
            prior_id,
        ),
        (
            ContextSelectionRole.OTHER_ADMITTED_JUDGMENT,
            OtherJudgmentContextVersionRef(
                InvestmentHypothesisVersionRef(other, JudgmentRevision(1))
            ),
            other,
        ),
        (
            ContextSelectionRole.SELECTED_ALTERNATIVE,
            DecisionAlternativeVersionRef(
                DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.PORTFOLIO_BOUNDARY,
            PortfolioBoundaryVersionRef(
                PortfolioBoundaryId(uuid4()), PortfolioBoundaryRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
            PortfolioStateVersionRef(
                PortfolioStateId(uuid4()), PortfolioStateRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.PROJECTED_PORTFOLIO_STATE,
            ProjectedPortfolioStateVersionRef(
                ProjectedPortfolioStateId(uuid4()), ProjectedPortfolioStateRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.INVESTMENT_MANDATE,
            InvestmentMandateVersionRef(
                InvestmentMandateId(uuid4()), InvestmentMandateRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.INVESTMENT_STRATEGY,
            InvestmentStrategyVersionRef(
                InvestmentStrategyId(uuid4()), InvestmentStrategyRevision(1)
            ),
            None,
        ),
        (
            ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
            InvestmentAuthorityRegimeVersionRef(
                InvestmentAuthorityRegimeId(uuid4()),
                InvestmentAuthorityRegimeRevision(1),
            ),
            None,
        ),
        (
            ContextSelectionRole.OUTCOME,
            OutcomeVersionRef(OutcomeId(uuid4()), OutcomeRevision(1)),
            None,
        ),
    )
    return tuple(
        CanonicalContextMeaning(
            role, reference, _selected(key, role, root or reference.root)
        )
        for role, reference, root in refs
    )


def test_every_material_r3_context_role_and_absence_uses_owner_proof() -> None:
    key = _key()
    owner = _OwnerDouble()
    resolver = OwnerMeaningResolver(owner)
    subjects = _context_cases(key)
    assert tuple(subject.role for subject in subjects) == tuple(ContextSelectionRole)
    for subject in subjects:
        assert isinstance(
            asyncio.run(resolver.read_current(key, subject, at=_T0)),
            OwnerMeaningWitness,
        )

    role = ContextSelectionRole.OUTCOME
    absence = CanonicalContextAbsence(
        role,
        ContextSelectionGuard(
            key, role, frozenset(), frozenset(), _SelectionUniverse(key, role)
        ),
    )
    assert isinstance(
        asyncio.run(resolver.read_current(key, absence, at=_T0)), OwnerMeaningWitness
    )


def test_same_version_lawful_time_change_and_observation_time_equality() -> None:
    key, subject, _, _ = _decision_setup()
    _, resolver, prior, fresh = _lawful_pair(key, subject)
    assert asyncio.run(resolver.verify(prior, validation_at=_T2)) == prior
    assert asyncio.run(resolver.verify(fresh, validation_at=_T2)) == fresh

    same = replace(
        prior,
        effective_at=_T1 + timedelta(hours=1),
        known_at=_T1 + timedelta(hours=1),
        read_at=_T1 + timedelta(hours=1),
    )
    assert same.semantic_identity == prior.semantic_identity


def test_unsupported_change_and_incomplete_cause_fail_closed() -> None:
    key = _key()
    subject = TargetJudgmentMeaning(
        InvestmentViewVersionRef(key.target, JudgmentRevision(1))
    )
    owner = _OwnerDouble()
    resolver = OwnerMeaningResolver(owner)
    valid = owner._expected(key, subject, _T0)
    owner.override = replace(valid, meaning="unsupported")
    result = asyncio.run(resolver.read_current(key, subject, at=_T0))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY

    owner.override = replace(
        valid,
        cause=replace(valid.cause, fact_ancestry=()),
    )
    result = asyncio.run(resolver.read_current(key, subject, at=_T0))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INCOMPLETE

    owner.corrections.append(_OwnerRecord(_T0, _T0, "correction support"))
    owner.override = valid
    result = asyncio.run(resolver.read_current(key, subject, at=_T0))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.INCOMPLETE


def test_same_version_change_needs_cause_for_target_claim_and_context() -> None:
    claim = ClaimId(uuid4())
    key = _key(claim=claim)
    subjects: tuple[OwnerMeaningSubject, ...] = (
        TargetJudgmentMeaning(
            InvestmentViewVersionRef(key.target, JudgmentRevision(1))
        ),
        ClaimMembershipMeaning(key.target, claim, ClaimCatalogVersion(1)),
        _context_cases(key)[2],
    )
    for subject in subjects:
        owner, resolver, _, fresh = _lawful_pair(key, subject)
        owner.override = replace(fresh, meaning="unsupported")
        rejected = asyncio.run(resolver.read_current(key, subject, at=_T2))
        assert isinstance(rejected, OwnerMeaningNoBasis)
        assert rejected.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_exact_key_guard_and_future_only_history_validity() -> None:
    key, subject, owner, resolver = _decision_setup()
    future = _OwnerRecord(_T2, _T0, "future")
    owner.records.append(future)
    initial = asyncio.run(resolver.read_current(key, subject, at=_T1))
    assert isinstance(initial, OwnerMeaningWitness)
    assert initial.meaning == "before"

    owner.records.append(_OwnerRecord(_T2, _T0, "conflict"))
    invalid = asyncio.run(resolver.read_current(key, subject, at=_T1))
    assert isinstance(invalid, OwnerMeaningNoBasis)
    assert invalid.reason is OwnerMeaningNoBasisReason.CONTRADICTORY

    owner.records.pop()
    wrong_key = _key()
    wrong_subject = GoverningDecisionMeaning(
        DecisionContextVersionRef(wrong_key.decision_id, DecisionVersion(1))
    )
    owner.override = owner._expected(wrong_key, wrong_subject, _T1)
    invalid = asyncio.run(resolver.read_current(key, subject, at=_T1))
    assert isinstance(invalid, OwnerMeaningNoBasis)
    assert invalid.reason is OwnerMeaningNoBasisReason.INVALID_HISTORY


def test_newly_recorded_future_only_fact_does_not_change_semantic_identity() -> None:
    key, subject, owner, resolver = _decision_setup()
    prior = asyncio.run(resolver.read_current(key, subject, at=_T1))
    assert isinstance(prior, OwnerMeaningWitness)

    owner.records.append(_OwnerRecord(_T2, _T1 + timedelta(hours=1), "future"))
    fresh = asyncio.run(
        resolver.read_current(key, subject, at=_T1 + timedelta(hours=2))
    )
    assert isinstance(fresh, OwnerMeaningWitness)
    assert prior.cause != fresh.cause
    assert prior.meaning == fresh.meaning
    assert prior.semantic_identity == fresh.semantic_identity
    assert (
        asyncio.run(resolver.verify(prior, validation_at=_T1 + timedelta(hours=2)))
        == prior
    )
    assert (
        asyncio.run(resolver.verify(fresh, validation_at=_T1 + timedelta(hours=2)))
        == fresh
    )


def test_context_witness_rejects_missing_selection_guard() -> None:
    key = _key()
    subject = _context_cases(key)[0]
    owner = _OwnerDouble()
    witness = owner._expected(key, subject, _T0)
    with pytest.raises(ValueError, match="selection guard"):
        replace(
            witness,
            cause=replace(witness.cause, relationship_guards=("unrelated",)),
        )


def test_typed_owner_subjects_cannot_be_rebound_to_another_key() -> None:
    key = _key()
    other = _key()
    owner = _OwnerDouble()
    resolver = OwnerMeaningResolver(owner)

    with pytest.raises(ValueError, match="governing Decision"):
        asyncio.run(resolver.read_current(other, _decision_subject(key), at=_T0))
    target = TargetJudgmentMeaning(
        InvestmentViewVersionRef(key.target, JudgmentRevision(1))
    )
    with pytest.raises(ValueError, match="target judgment"):
        asyncio.run(resolver.read_current(other, target, at=_T0))
    with pytest.raises(ValueError, match="context selection"):
        asyncio.run(resolver.read_current(other, _context_cases(key)[0], at=_T0))
    with pytest.raises(TypeError, match="closed typed variant"):
        asyncio.run(resolver.read_current(key, object(), at=_T0))
    assert owner.calls == []


def test_distinct_no_basis_outcomes_and_unavailability() -> None:
    key, subject, owner, resolver = _decision_setup()
    for reason in OwnerMeaningNoBasisReason:
        owner.override = OwnerMeaningNoBasis(
            key, subject, _T0, _T0, _T0, reason, "owner result"
        )
        result = asyncio.run(resolver.read_current(key, subject, at=_T0))
        assert isinstance(result, OwnerMeaningNoBasis)
        assert result.reason is reason
    owner.unavailable = True
    result = asyncio.run(resolver.read_current(key, subject, at=_T0))
    assert isinstance(result, OwnerMeaningNoBasis)
    assert result.reason is OwnerMeaningNoBasisReason.UNAVAILABLE
