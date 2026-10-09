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
from polaris.application.evidence.reconstruction import EvidenceHistories
from polaris.application.evidence.requirements import (
    MissingEvidenceRequirementAuthority,
    ResolvedEvidenceRequirementVersion,
)
from polaris.application.evidence.sufficiency import EvidenceSufficiencyBasis
from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.configuration import (
    EvidenceRequirementApplicabilityKey,
    EvidenceRequirementSetVersion,
    InvestmentHorizon,
)
from polaris.domain.decisions import InvestmentDecision
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

    async def load_current_decision_state(
        self, decision_id: object, *, known_at: datetime
    ) -> DecisionMemoryCurrentState | None:
        self.at = known_at
        if decision_id != self.decision.decision_id:
            return None
        return DecisionMemoryCurrentState(
            self.decision.history, self.decision.version, ()
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


# This current-basis fake independently fixes historical Configuration authority;
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
        # This current-basis fixture independently constructs observation ancestry;
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
    version = version or EvidenceSupportVersion(1)
    epochs = _Epochs(version)
    query = CurrentEvidenceBasisQuery(
        decisions=DecisionMemoryService(reader=owner),
        targets=TargetJudgmentResolver(target),
        contexts=ContextSelectionResolver(contexts),
        requirement_keys=_RequirementKeys(applicability_key),
        sufficiency=_Sufficiency(version, applicability_key, empty=empty),
        evidence=_Evidence(
            histories if histories is not None else _histories(), key.target
        ),
        support_epochs=epochs,
        claims=_Claims(claim_result),
        requirements=_Requirements(),
    )
    return query, key, target, contexts, epochs, owner


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
    query, key, *_ = _query(
        applicability_key=application_key,
        histories=EvidenceHistories((), (), ()),
        empty=True,
        target_version=version,
    )
    result = asyncio.run(query.read(key, at=AT))
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.target.version == version


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
    claim_id = ClaimId(uuid4())
    application_key = replace(
        requirement_key(), scope=ClaimSpecificEvidenceScope(claim_id)
    )
    membership = ResolvedClaimMembership(
        application_key.target, claim_id, ClaimCatalogVersion(3)
    )
    # The claim-specific proof independently builds an empty selected family so claim
    # catalog capture is visible.
    # arid: disable
    query, key, *_ = _query(
        applicability_key=application_key,
        histories=EvidenceHistories((), (), ()),
        empty=True,
        claim_result=membership,
    )
    result = asyncio.run(query.read(key, at=AT))
    # arid: enable
    assert isinstance(result, CurrentEvidenceBasis)
    assert result.claim_catalog_version == ClaimCatalogVersion(3)
    assert result.guards.claim is not None
    assert result.guards.claim.membership == membership


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
    # The second claim-catalog candidate repeats setup deliberately so only its owner
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
    # The second requirement candidate repeats setup deliberately so only requirement
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
    # This binding correction is constructed locally to prove current support and
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
    # This restoration falsifier constructs its own correction branch independently of
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
    # This restoration candidate repeats exact owner setup so the changed correction
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
    # This assessment-retraction candidate repeats exact owner setup to isolate the new
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
