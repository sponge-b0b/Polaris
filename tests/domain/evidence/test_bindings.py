from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from typing import cast
from uuid import UUID, uuid4

import pytest

from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceMaterialQualification,
    EvidenceRole,
    InvalidEvidenceBinding,
)
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessBasisReference,
    EvidenceFreshnessEvaluation,
    EvidenceFreshnessMissingAuthority,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    DecisionEvaluationRef,
    EvidenceJudgmentFamily,
    EvidenceJudgmentRef,
    EvidenceScope,
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
    evidence_judgment_family,
)
from polaris.domain.evidence.observations import (
    EvidenceBindingId,
    EvidenceObservationId,
)
from tests.binding_support import BINDING_EFFECTIVE_AT, BINDING_RECORDED_AT
from tests.configuration_support import requirement_key


def _binding(
    *,
    binding_id: UUID | None = None,
    target: EvidenceJudgmentRef | None = None,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    materially_used: bool = True,
    scope: EvidenceScope | None = None,
    freshness: EvidenceFreshnessEvaluation | None = None,
) -> EvidenceBinding:
    resolved_target = target or InvestmentRecommendationRef(uuid4())
    resolved_scope = scope or JudgmentWideEvidenceScope()
    return EvidenceBinding(
        binding_id=EvidenceBindingId(binding_id or uuid4()),
        observation_id=EvidenceObservationId(uuid4()),
        target=resolved_target,
        scope=resolved_scope,
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
        role=EvidenceRole.SUPPORTING,
        availability=availability,
        materially_used=materially_used,
        effective_at=BINDING_EFFECTIVE_AT,
        recorded_at=BINDING_RECORDED_AT,
        freshness=(
            freshness
            or EvidenceFreshnessMissingAuthority(
                EvidenceFreshnessBasisReference(
                    "basis:exact",
                    BINDING_EFFECTIVE_AT,
                    replace(
                        requirement_key(),
                        target=resolved_target,
                        scope=resolved_scope,
                        evidence_use=EvidenceUse.JUDGMENT_BASIS,
                    ),
                )
            )
        ),
        material_qualification=EvidenceMaterialQualification("qualified"),
    )


def test_binding_target_union_is_exactly_the_ten_accepted_families() -> None:
    targets = (
        InvestmentHypothesisRef(uuid4()),
        InvestmentViewRef(uuid4()),
        MeaningfulChallengeResultRef(uuid4()),
        ProjectedPortfolioConsequenceRef(uuid4()),
        PortfolioRiskAssessmentRef(uuid4()),
        InvestmentRecommendationRef(uuid4()),
        RecommendationWithholdingJudgmentRef(uuid4()),
        HumanInvestmentDecisionRef(uuid4()),
        DecisionEvaluationRef(uuid4()),
        LessonRef(uuid4()),
    )

    assert {evidence_judgment_family(target) for target in targets} == set(
        EvidenceJudgmentFamily
    )
    for target in targets:
        assert _binding(target=target).target == target

    with pytest.raises(TypeError, match="EvidenceJudgmentRef"):
        _binding(target=cast(EvidenceJudgmentRef, InvestmentDecisionId(uuid4())))


def test_role_and_use_vocabularies_are_closed_and_independent() -> None:
    assert {item.value for item in EvidenceRole} == {
        "supporting",
        "conflicting",
        "constraining",
        "qualifying",
        "contextual",
        "reconstruction",
    }
    assert {item.value for item in EvidenceUse} == {
        "judgment_basis",
        "challenge_basis",
        "current_support_check",
        "retrospective_later_evidence",
        "reconstruction_only",
    }


def test_material_use_requires_available_judgment_time_evidence() -> None:
    for availability in (
        EvidenceAvailability.UNAVAILABLE,
        EvidenceAvailability.UNKNOWN,
    ):
        with pytest.raises(InvalidEvidenceBinding, match="AVAILABLE"):
            _binding(availability=availability, materially_used=True)

    assert (
        _binding(
            availability=EvidenceAvailability.UNKNOWN,
            materially_used=False,
        ).availability
        is EvidenceAvailability.UNKNOWN
    )


def test_scope_is_exactly_judgment_wide_or_claim_specific() -> None:
    claim_id = ClaimId(uuid4())

    assert isinstance(_binding().scope, JudgmentWideEvidenceScope)
    assert _binding(scope=ClaimSpecificEvidenceScope(claim_id)).scope == (
        ClaimSpecificEvidenceScope(claim_id)
    )

    with pytest.raises(TypeError, match="EvidenceScope"):
        _binding(scope=cast(EvidenceScope, object()))


def test_binding_endpoints_are_fixed_and_duplicate_tuples_remain_distinct() -> None:
    first = _binding()
    second = _binding(
        target=first.target,
    )

    assert first.binding_id != second.binding_id
    assert first.target == second.target
    with pytest.raises(FrozenInstanceError):
        first.__setattr__("target", InvestmentRecommendationRef(uuid4()))


def test_binding_requires_typed_freshness_evaluation() -> None:
    binding = _binding()

    assert isinstance(binding.freshness, EvidenceFreshnessMissingAuthority)

    with pytest.raises(TypeError, match="EvidenceFreshnessEvaluation"):
        _binding(freshness=cast(EvidenceFreshnessEvaluation, object()))


def test_binding_rejects_freshness_basis_for_different_endpoint() -> None:
    target = InvestmentRecommendationRef(uuid4())
    other = InvestmentRecommendationRef(uuid4())
    freshness = EvidenceFreshnessMissingAuthority(
        EvidenceFreshnessBasisReference(
            "basis:wrong-target",
            BINDING_EFFECTIVE_AT,
            replace(requirement_key(), target=other),
        )
    )

    with pytest.raises(InvalidEvidenceBinding, match="freshness applicability"):
        _binding(target=target, freshness=freshness)
