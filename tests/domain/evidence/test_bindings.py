from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import cast
from uuid import UUID, uuid4

import pytest

from polaris.domain.configuration import (
    EvidenceRequirementId,
    EvidenceRequirementSetId,
    EvidenceRequirementSetVersionId,
)
from polaris.domain.decisions import InvestmentDecisionId
from polaris.domain.evidence import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    DecisionEvaluationRef,
    EvidenceAvailability,
    EvidenceBinding,
    EvidenceBindingId,
    EvidenceFreshnessAuthorityReference,
    EvidenceFreshnessBasisReference,
    EvidenceJudgmentFamily,
    EvidenceJudgmentRef,
    EvidenceMaterialQualification,
    EvidenceObservationId,
    EvidenceRole,
    EvidenceScope,
    EvidenceUse,
    HumanInvestmentDecisionRef,
    InvalidEvidenceBinding,
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
from tests.binding_support import BINDING_EFFECTIVE_AT, BINDING_RECORDED_AT


def _binding(
    *,
    binding_id: UUID | None = None,
    target: EvidenceJudgmentRef | None = None,
    availability: EvidenceAvailability = EvidenceAvailability.AVAILABLE,
    materially_used: bool = True,
    scope: EvidenceScope | None = None,
    freshness: bool = False,
) -> EvidenceBinding:
    return EvidenceBinding(
        binding_id=EvidenceBindingId(binding_id or uuid4()),
        observation_id=EvidenceObservationId(uuid4()),
        target=(target or InvestmentRecommendationRef(uuid4())),
        scope=(scope or JudgmentWideEvidenceScope()),
        evidence_use=EvidenceUse.JUDGMENT_BASIS,
        role=EvidenceRole.SUPPORTING,
        availability=availability,
        materially_used=materially_used,
        effective_at=BINDING_EFFECTIVE_AT,
        recorded_at=BINDING_RECORDED_AT,
        material_qualification=EvidenceMaterialQualification("qualified"),
        freshness_authority=(
            EvidenceFreshnessAuthorityReference(
                EvidenceRequirementSetId(uuid4()),
                EvidenceRequirementSetVersionId(uuid4()),
                EvidenceRequirementId(uuid4()),
            )
            if freshness
            else None
        ),
        freshness_basis=(
            EvidenceFreshnessBasisReference("basis:exact") if freshness else None
        ),
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


def test_claim_specific_scope_is_rejected_until_target_catalog_admission_exists() -> (
    None
):
    with pytest.raises(InvalidEvidenceBinding, match="claim validation"):
        _binding(scope=ClaimSpecificEvidenceScope(ClaimId(uuid4())))


def test_binding_endpoints_are_fixed_and_duplicate_tuples_remain_distinct() -> None:
    first = _binding()
    second = _binding(
        target=first.target,
    )

    assert first.binding_id != second.binding_id
    assert first.target == second.target
    with pytest.raises(FrozenInstanceError):
        first.__setattr__("target", InvestmentRecommendationRef(uuid4()))


def test_freshness_authority_and_basis_references_are_atomic() -> None:
    full = _binding(freshness=True)
    assert full.freshness_authority is not None
    assert full.freshness_basis is not None

    with pytest.raises(InvalidEvidenceBinding, match="present together"):
        EvidenceBinding(
            binding_id=EvidenceBindingId(uuid4()),
            observation_id=EvidenceObservationId(uuid4()),
            target=InvestmentRecommendationRef(uuid4()),
            scope=JudgmentWideEvidenceScope(),
            evidence_use=EvidenceUse.JUDGMENT_BASIS,
            role=EvidenceRole.SUPPORTING,
            availability=EvidenceAvailability.AVAILABLE,
            materially_used=True,
            effective_at=BINDING_EFFECTIVE_AT,
            recorded_at=BINDING_RECORDED_AT,
            freshness_basis=EvidenceFreshnessBasisReference("basis:orphan"),
        )
