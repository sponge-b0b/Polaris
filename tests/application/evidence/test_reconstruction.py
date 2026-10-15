from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from polaris.application.decisions import DecisionMemoryService
from polaris.application.evidence.claims import (
    ClaimNotCurrent,
    ClaimNotKnownAtCutoff,
    ClaimNotYetEffective,
    ClaimTargetNotKnownAtCutoff,
    ClaimTargetNotYetEffective,
    ContestedClaimHistory,
    InvalidClaimHistory,
    InvalidClaimReference,
    ResolvedClaimMembership,
    UnavailableClaimCatalog,
)
from polaris.application.evidence.reconstruction import (
    CompleteReconstruction,
    ContestedReconstruction,
    EvidenceHistories,
    HistoricalEvidenceQuery,
    HistoricalEvidenceRequest,
    IncompleteReconstruction,
    ReconstructionInvalidHistory,
    ReconstructionInvalidReference,
    ReconstructionNotEffective,
    ReconstructionNotKnown,
    ReconstructionSubject,
    ReconstructionUnavailable,
    TargetContext,
    TargetContextContested,
    TargetContextIncomplete,
    TargetContextUnavailable,
    TargetInvalidReference,
    TargetNotEffective,
    TargetNotKnown,
)
from polaris.application.evidence.requirements import (
    ResolvedEvidenceRequirementVersion,
)
from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.decisions import (
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionScope,
    DecisionSubject,
    InvestmentDecisionId,
    OperationId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    initiate_decision,
)
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
    EvidenceObservation,
    EvidenceObservationCorrection,
    EvidenceObservationCorrectionHistory,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
    EvidenceUse,
)
from polaris.domain.evidence.bindings import EvidenceAvailability, EvidenceRole
from polaris.domain.evidence.freshness import EvidenceFreshnessBasisReference
from polaris.domain.evidence.sufficiency import EvidenceSufficiencyResult
from tests.configuration_support import (
    SECOND_VERSION_ID,
    requirement_assignment_for_key,
    requirement_key,
    requirement_version,
)
from tests.sufficiency_support import derived_assessment, interpreted_binding

BOUNDARY = datetime(2026, 9, 29, 14, 4, tzinfo=UTC)


def _decision():
    recorded = BOUNDARY - timedelta(days=1)
    attribution = KnownActorAttribution(ActorId(uuid4()))
    operation_id = OperationId(uuid4())
    trigger = TriggerProvenance(TriggerKind.HUMAN_REQUEST, "historical query fixture")
    technical = TechnicalProvenance(
        (TechnicalReference(TechnicalReferenceKind.TRACE, "query fixture"),)
    )
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Choose portfolio exposure",
        recorded,
        recorded,
        operation_id,
        attribution,
        trigger,
        technical,
    )
    return initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("Portfolio exposure"),
        scope=DecisionScope.unresolved(),
        # duplicate-code: this Evidence-query fixture independently constructs a
        # valid Decision; sharing another domain suite's fixture would couple proofs.
        # arid: disable
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=recorded,
        ),
        # arid: enable
        mutation=DecisionMutationContext(
            DecisionLifecycleFactId(uuid4()),
            operation_id,
            attribution,
            trigger,
            recorded,
            recorded,
            technical,
        ),
    )


class _DecisionReader:
    def __init__(self, decision) -> None:
        self.decision = decision

    async def load_decision_history(self, decision_id):
        return (
            self.decision.history if decision_id == self.decision.decision_id else None
        )

    async def load_relationship_history(self):
        return ()


class _Targets:
    def __init__(self, result) -> None:
        self.result = result

    async def load_target_context(self, target, *, effective_at, known_at):
        assert effective_at.tzinfo is not None
        assert known_at.tzinfo is not None
        return self.result


class _Evidence:
    def __init__(self, histories: EvidenceHistories) -> None:
        self.histories = histories

    async def load_target_histories(self, target):
        assert target == requirement_key().target
        return self.histories


class _Claims:
    async def resolve(self, target, claim_id, *, effective_at, known_at):
        raise AssertionError("judgment-wide bindings must not consult claim membership")


class _Requirements:
    async def resolve(self, key, *, effective_at, known_at):
        assert key == requirement_key()
        assert effective_at <= known_at
        return ResolvedEvidenceRequirementVersion(requirement_version())


def _histories(*, correction=None, retrospective=False) -> EvidenceHistories:
    binding = interpreted_binding().binding
    observation = EvidenceObservation(
        binding.observation_id,
        EvidenceSourceProvenance("provider", "release", "publisher"),
        EvidenceSubjectReference("market_price", "SPY"),
        binding.effective_at,
        binding.effective_at,
        EvidenceObservationMaterial(retained_representation="100"),
        binding.effective_at,
    )
    observation_history = EvidenceObservationCorrectionHistory(
        observation,
        binding.recorded_at,
        (correction,) if correction is not None else (),
    )
    binding_history = EvidenceBindingCorrectionHistory(binding, ())
    bindings: tuple[EvidenceBindingCorrectionHistory, ...] = (binding_history,)
    if retrospective:
        later_key = replace(
            requirement_key(), evidence_use=EvidenceUse.RETROSPECTIVE_LATER_EVIDENCE
        )
        later = replace(
            binding,
            binding_id=type(binding.binding_id)(
                UUID("00000000-0000-4000-8000-000000000099")
            ),
            evidence_use=EvidenceUse.RETROSPECTIVE_LATER_EVIDENCE,
            recorded_at=BOUNDARY + timedelta(minutes=1),
            freshness=replace(
                binding.freshness,
                basis=EvidenceFreshnessBasisReference(
                    "test:later", BOUNDARY, later_key
                ),
            ),
        )
        bindings += (EvidenceBindingCorrectionHistory(later, ()),)
    assessment = EvidenceAssessmentCorrectionHistory(derived_assessment(), ())
    return EvidenceHistories((observation_history,), bindings, (assessment,))


def _query(
    histories: EvidenceHistories,
    target_result=None,
    requirements=None,
    claims=None,
):
    decision = _decision()
    target = requirement_key().target
    result = target_result or TargetContext(decision.decision_id, target, "owner fact")
    service = HistoricalEvidenceQuery(
        decisions=DecisionMemoryService(reader=_DecisionReader(decision)),
        targets=_Targets(result),
        evidence=_Evidence(histories),
        claims=claims or _Claims(),
        requirements=requirements or _Requirements(),
    )
    return service, HistoricalEvidenceRequest(
        decision.decision_id, target, BOUNDARY, BOUNDARY
    )


def _one_minute_later(query, request):
    return asyncio.run(
        query.reconstruct(replace(request, known_at=BOUNDARY + timedelta(minutes=1)))
    )


def _with_second_assessment(source: EvidenceHistories, assessment):
    return replace(
        source,
        assessments=(
            source.assessments[0],
            EvidenceAssessmentCorrectionHistory(assessment, ()),
        ),
    )


def test_historical_query_requires_typed_identity_target_and_aware_boundaries() -> None:
    _, request = _query(_histories())
    for kwargs, error in (
        ({"decision_id": "not a Decision ID"}, TypeError),
        ({"target": "not a target"}, TypeError),
        ({"effective_at": BOUNDARY.replace(tzinfo=None)}, ValueError),
        ({"known_at": BOUNDARY.replace(tzinfo=None)}, ValueError),
    ):
        with pytest.raises(error):
            replace(request, **kwargs)


def test_context_evidence_and_retrospective_later_evidence_stay_separate() -> None:
    query, request = _query(_histories(retrospective=True))
    result = asyncio.run(query.reconstruct(request))
    assert isinstance(result, CompleteReconstruction)
    assert result.view.context.target.fact == "owner fact"
    assert result.view.context.decision.decision_id == request.decision_id
    assert len(result.view.judgment_time_bindings) == 1
    assert result.view.retrospective_later_bindings == ()
    assert result.view.judgment_time_bindings[0].root.availability.value == "available"
    assert result.view.assessments[0].root.requirement_version_id == (
        requirement_version().version_id
    )
    assert result.view.observations[0].root.source.source_authority == "publisher"


@pytest.mark.parametrize(
    ("evidence_use", "field"),
    (
        (EvidenceUse.JUDGMENT_BASIS, "judgment_time_bindings"),
        (EvidenceUse.CHALLENGE_BASIS, "judgment_time_bindings"),
        (EvidenceUse.CURRENT_SUPPORT_CHECK, "current_support_bindings"),
        (EvidenceUse.RETROSPECTIVE_LATER_EVIDENCE, "retrospective_later_bindings"),
        (EvidenceUse.RECONSTRUCTION_ONLY, "reconstruction_only_bindings"),
    ),
)
def test_each_evidence_use_keeps_its_historical_partition(evidence_use, field) -> None:
    source = _histories()
    binding = source.bindings[0].root
    key = replace(requirement_key(), evidence_use=evidence_use)
    binding = replace(
        binding,
        evidence_use=evidence_use,
        freshness=replace(
            binding.freshness,
            basis=EvidenceFreshnessBasisReference("use partition", BOUNDARY, key),
        ),
    )
    source = replace(
        source,
        bindings=(EvidenceBindingCorrectionHistory(binding, ()),),
        assessments=(),
    )
    query, request = _query(source)
    result = asyncio.run(query.reconstruct(request))
    assert isinstance(result, CompleteReconstruction)
    for candidate in (
        "judgment_time_bindings",
        "current_support_bindings",
        "retrospective_later_bindings",
        "reconstruction_only_bindings",
    ):
        assert len(getattr(result.view, candidate)) == int(candidate == field)


def test_decision_temporal_and_target_association_failures_are_distinct() -> None:
    query, request = _query(_histories())
    unknown = asyncio.run(
        query.reconstruct(replace(request, decision_id=InvestmentDecisionId(uuid4())))
    )
    assert isinstance(unknown, ReconstructionNotKnown)
    assert unknown.subject is ReconstructionSubject.DECISION

    not_effective = asyncio.run(
        query.reconstruct(replace(request, effective_at=BOUNDARY - timedelta(days=2)))
    )
    assert isinstance(not_effective, ReconstructionNotEffective)
    assert not_effective.subject is ReconstructionSubject.DECISION

    wrong_owner = TargetContext(InvestmentDecisionId(uuid4()), request.target, "fact")
    query, request = _query(_histories(), target_result=wrong_owner)
    assert isinstance(
        asyncio.run(query.reconstruct(request)), ReconstructionInvalidReference
    )


def test_later_observation_revision_cannot_change_earlier_knowledge() -> None:
    original = _histories().observations[0].root
    correction = EvidenceObservationCorrection(
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000701")),
        original.observation_id,
        original.observation_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("publisher revision"),
        original.effective_at,
        BOUNDARY + timedelta(minutes=1),
        replace(
            original,
            material=EvidenceObservationMaterial(retained_representation="101"),
        ),
    )
    query, request = _query(_histories(correction=correction))
    earlier = asyncio.run(query.reconstruct(request))
    assert isinstance(earlier, CompleteReconstruction)
    assert earlier.view.observations[0].interpretation.assertions == frozenset(
        {original}
    )
    later = _one_minute_later(query, request)
    assert isinstance(later, CompleteReconstruction)
    assert later.view.observations[0].interpretation.assertions == frozenset(
        {correction.replacement}
    )


def test_binding_revision_keeps_earlier_role_and_availability() -> None:
    source = _histories()
    binding = source.bindings[0].root
    revised = replace(
        binding,
        role=EvidenceRole.CONFLICTING,
        availability=EvidenceAvailability.UNKNOWN,
        materially_used=False,
    )
    # duplicate-code: this historical binding-revision falsifier constructs its
    # own fixed-endpoint correction; sharing assessment or adapter setup would
    # couple independently meaningful correction-family proofs.
    # arid: disable
    correction = EvidenceBindingCorrection(
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000705")),
        binding.binding_id,
        binding.binding_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("availability correction"),
        binding.effective_at,
        BOUNDARY + timedelta(minutes=1),
        revised,
    )
    source = replace(
        source,
        bindings=(replace(source.bindings[0], corrections=(correction,)),),
    )
    # arid: enable
    query, request = _query(source)
    earlier = asyncio.run(query.reconstruct(request))
    assert isinstance(earlier, CompleteReconstruction)
    assert earlier.view.judgment_time_bindings[0].interpretation.assertions == (
        frozenset({binding})
    )
    later = _one_minute_later(query, request)
    assert isinstance(later, CompleteReconstruction)
    assert later.view.judgment_time_bindings[0].interpretation.assertions == (
        frozenset({revised})
    )


def test_claim_membership_is_checked_at_binding_history_boundary() -> None:
    source = _histories()
    binding = source.bindings[0].root
    claim_id = ClaimId(UUID("00000000-0000-4000-8000-000000000706"))
    scope = ClaimSpecificEvidenceScope(claim_id)
    key = replace(requirement_key(), scope=scope)
    claim_binding = replace(
        binding,
        scope=scope,
        freshness=replace(
            binding.freshness,
            basis=EvidenceFreshnessBasisReference("claim basis", BOUNDARY, key),
        ),
    )
    source = replace(
        source, bindings=(EvidenceBindingCorrectionHistory(claim_binding, ()),)
    )

    class _HistoricalClaims:
        async def resolve(self, target, asked_claim, *, effective_at, known_at):
            assert asked_claim == claim_id
            if known_at != binding.recorded_at:
                return InvalidClaimReference(target, asked_claim)
            return ResolvedClaimMembership(target, asked_claim, ClaimCatalogVersion(1))

    query, request = _query(source, claims=_HistoricalClaims())
    later = asyncio.run(
        query.reconstruct(replace(request, known_at=BOUNDARY + timedelta(days=1)))
    )
    assert isinstance(later, CompleteReconstruction)

    class _ClaimOutcome:
        def __init__(self, outcome) -> None:
            self.outcome = outcome

        async def resolve(self, target, asked_claim, *, effective_at, known_at):
            return self.outcome

    for claim_outcome, result_type, subject in (
        (
            ClaimNotKnownAtCutoff(binding.target, claim_id),
            ReconstructionNotKnown,
            ReconstructionSubject.CLAIM,
        ),
        (
            ClaimTargetNotKnownAtCutoff(binding.target),
            ReconstructionNotKnown,
            ReconstructionSubject.TARGET,
        ),
        (
            ClaimNotYetEffective(binding.target, claim_id),
            ReconstructionNotEffective,
            ReconstructionSubject.CLAIM,
        ),
        (
            ClaimTargetNotYetEffective(binding.target),
            ReconstructionNotEffective,
            ReconstructionSubject.TARGET,
        ),
    ):
        query, request = _query(source, claims=_ClaimOutcome(claim_outcome))
        result = asyncio.run(query.reconstruct(request))
        assert isinstance(result, result_type)
        assert result.subject is subject

    query, request = _query(
        source, claims=_ClaimOutcome(InvalidClaimReference(binding.target, claim_id))
    )
    assert isinstance(
        asyncio.run(query.reconstruct(request)), ReconstructionInvalidReference
    )

    query, request = _query(
        source,
        claims=_ClaimOutcome(
            ResolvedClaimMembership(
                binding.target, ClaimId(uuid4()), ClaimCatalogVersion(1)
            )
        ),
    )
    assert isinstance(
        asyncio.run(query.reconstruct(request)), ReconstructionInvalidReference
    )

    all_outcomes = (
        ResolvedClaimMembership(binding.target, claim_id, ClaimCatalogVersion(1)),
        ClaimTargetNotKnownAtCutoff(binding.target),
        ClaimNotKnownAtCutoff(binding.target, claim_id),
        ClaimTargetNotYetEffective(binding.target),
        ClaimNotYetEffective(binding.target, claim_id),
        ClaimNotCurrent(binding.target, claim_id),
        InvalidClaimReference(binding.target, claim_id),
        ContestedClaimHistory(binding.target, "contested"),
        InvalidClaimHistory(binding.target, "invalid"),
        UnavailableClaimCatalog(binding.target, "unavailable"),
    )
    for outcome in all_outcomes:
        wrong_target = replace(outcome, target=replace(binding.target, value=uuid4()))
        query, request = _query(source, claims=_ClaimOutcome(wrong_target))
        assert isinstance(
            asyncio.run(query.reconstruct(request)), ReconstructionInvalidReference
        )
        if hasattr(outcome, "claim_id"):
            wrong_claim = replace(outcome, claim_id=ClaimId(uuid4()))
            query, request = _query(source, claims=_ClaimOutcome(wrong_claim))
            assert isinstance(
                asyncio.run(query.reconstruct(request)), ReconstructionInvalidReference
            )


def test_unavailable_evidence_is_a_domain_result() -> None:
    source = _histories()
    interpretation = interpreted_binding(
        availability=EvidenceAvailability.UNAVAILABLE, materially_used=False
    )
    source = replace(
        source,
        bindings=(EvidenceBindingCorrectionHistory(interpretation.binding, ()),),
        assessments=(
            EvidenceAssessmentCorrectionHistory(
                derived_assessment(interpretations=(interpretation,)), ()
            ),
        ),
    )
    query, request = _query(source)
    result = asyncio.run(query.reconstruct(request))
    assert isinstance(result, CompleteReconstruction)
    assert result.view.judgment_time_bindings[0].root.availability is (
        EvidenceAvailability.UNAVAILABLE
    )
    assert result.view.current_assessments[0].root.result is (
        EvidenceSufficiencyResult.INSUFFICIENT
    )


def test_missing_referenced_observation_is_safe_incomplete() -> None:
    source = _histories()
    query, request = _query(replace(source, observations=()))
    result = asyncio.run(query.reconstruct(request))
    assert isinstance(result, IncompleteReconstruction)
    assert result.safe_partial is not None
    assert result.safe_partial.observations == ()


def test_later_reassessment_preserves_original_proof_and_changes_current_root() -> None:
    source = _histories()
    original = source.assessments[0].root
    reassessment = replace(
        derived_assessment(2),
        reassesses_assessment_id=original.assessment_id,
        recorded_at=BOUNDARY + timedelta(minutes=1),
    )
    source = _with_second_assessment(source, reassessment)
    query, request = _query(source)
    earlier = asyncio.run(query.reconstruct(request))
    assert isinstance(earlier, CompleteReconstruction)
    assert tuple(
        item.root.assessment_id for item in earlier.view.current_assessments
    ) == (original.assessment_id,)
    later = _one_minute_later(query, request)
    assert isinstance(later, CompleteReconstruction)
    assert tuple(
        item.root.assessment_id for item in later.view.current_assessments
    ) == (reassessment.assessment_id,)
    assert later.view.assessments[0].root == earlier.view.assessments[0].root


def test_assessment_revision_is_known_only_after_its_recording_cutoff() -> None:
    source = _histories()
    original = source.assessments[0].root
    revised = replace(original, attribution=KnownActorAttribution(ActorId(uuid4())))
    correction = EvidenceAssessmentCorrection(
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000704")),
        original.assessment_id,
        original.assessment_id,
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("attribution correction"),
        original.effective_at,
        BOUNDARY + timedelta(minutes=1),
        revised,
    )
    source = replace(
        source,
        assessments=(replace(source.assessments[0], corrections=(correction,)),),
    )
    query, request = _query(source)
    earlier = asyncio.run(query.reconstruct(request))
    assert isinstance(earlier, CompleteReconstruction)
    assert earlier.view.assessments[0].interpretation.assertions == frozenset(
        {original}
    )
    later = _one_minute_later(query, request)
    assert isinstance(later, CompleteReconstruction)
    assert later.view.assessments[0].interpretation.assertions == frozenset({revised})
    assert later.view.assessments[0].root.requirement_version_id == (
        original.requirement_version_id
    )


def test_assessment_retraction_preserves_root_proof_without_current_assertion() -> None:
    source = _histories()
    original = source.assessments[0].root
    retraction = EvidenceAssessmentCorrection(
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000707")),
        original.assessment_id,
        original.assessment_id,
        EvidenceCorrectionEffect.RETRACT,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("retracted assessment"),
        original.effective_at,
        BOUNDARY + timedelta(minutes=1),
    )
    source = replace(
        source,
        assessments=(replace(source.assessments[0], corrections=(retraction,)),),
    )
    query, request = _query(source)
    earlier = asyncio.run(query.reconstruct(request))
    assert isinstance(earlier, CompleteReconstruction)
    assert len(earlier.view.current_assessments) == 1
    later = _one_minute_later(query, request)
    assert isinstance(later, CompleteReconstruction)
    assert later.view.assessments[0].root.requirement_assessments == (
        original.requirement_assessments
    )
    assert later.view.assessments[0].interpretation.state is (
        EvidenceInterpretationState.WITHDRAWN
    )
    assert later.view.current_assessments == ()


def test_competing_assessment_roots_are_contested() -> None:
    source = _histories()
    source = _with_second_assessment(source, derived_assessment(2))
    query, request = _query(source)
    result = asyncio.run(query.reconstruct(request))
    assert isinstance(result, ContestedReconstruction)
    assert result.safe_partial is not None
    assert len(result.safe_partial.current_assessments) == 2


def test_changed_requirement_authority_does_not_replace_original_proof() -> None:
    source = _histories()

    class _ChangedRequirements:
        async def resolve(self, key, *, effective_at, known_at):
            assert known_at == source.assessments[0].root.known_at
            return ResolvedEvidenceRequirementVersion(
                requirement_version(SECOND_VERSION_ID)
            )

    query, request = _query(source, requirements=_ChangedRequirements())
    assert isinstance(
        asyncio.run(query.reconstruct(request)), ReconstructionInvalidHistory
    )

    for version in (
        requirement_version(set_id=uuid4()),
        replace(
            requirement_version(),
            applicability=requirement_assignment_for_key(
                replace(requirement_key(), evidence_use=EvidenceUse.CHALLENGE_BASIS)
            ),
        ),
        replace(requirement_version(), recorded_at=BOUNDARY + timedelta(days=1)),
    ):

        class _MismatchedRequirements:
            def __init__(self, selected_version) -> None:
                self.version = selected_version

            async def resolve(self, key, *, effective_at, known_at):
                return ResolvedEvidenceRequirementVersion(self.version)

        query, request = _query(source, requirements=_MismatchedRequirements(version))
        assert isinstance(
            asyncio.run(query.reconstruct(request)), ReconstructionInvalidHistory
        )


def test_target_result_families_remain_distinct() -> None:
    cases = (
        (TargetNotKnown(), ReconstructionNotKnown),
        (TargetNotEffective(), ReconstructionNotEffective),
        (TargetInvalidReference("wrong Decision"), ReconstructionInvalidReference),
        (TargetContextIncomplete("missing fact"), IncompleteReconstruction),
        (TargetContextContested("competing facts"), ContestedReconstruction),
        (TargetContextUnavailable("store down"), ReconstructionUnavailable),
    )
    for target_result, expected in cases:
        query, request = _query(_histories(), target_result)
        assert isinstance(asyncio.run(query.reconstruct(request)), expected)


def test_invalid_correction_ancestry_fails_closed() -> None:
    source = _histories()
    observation = source.observations[0].root
    invalid = EvidenceObservationCorrection(
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000702")),
        observation.observation_id,
        EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000703")),
        EvidenceCorrectionEffect.REVISE,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("missing ancestor"),
        observation.effective_at,
        BOUNDARY,
        observation,
    )
    source = replace(
        source,
        observations=(replace(source.observations[0], corrections=(invalid,)),),
    )
    query, request = _query(source)
    assert isinstance(
        asyncio.run(query.reconstruct(request)), ReconstructionInvalidHistory
    )
