from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest

from polaris.domain.configuration import (
    EvidenceRequirementId,
    FreshnessRequirementDefinition,
    SufficiencyRequirementApplicabilityState,
    SufficiencyRequirementDefinition,
)
from polaris.domain.evidence.bindings import EvidenceAvailability, EvidenceRole
from polaris.domain.evidence.observations import EvidenceSubjectReference
from polaris.domain.evidence.sufficiency import (
    EvidenceBindingInterpretationState,
    EvidenceRequirementDeficiencyReason,
    EvidenceRequirementDisposition,
    EvidenceSufficiencyResult,
    InvalidEvidenceSufficiency,
    evaluate_evidence_sufficiency,
)
from polaris.domain.evidence.sufficiency_requirements import MinimumEligibleEvidence
from tests.configuration_support import requirement_key, requirement_version
from tests.sufficiency_support import (
    ASSESSMENT_EFFECTIVE_AT,
    ASSESSMENT_KNOWN_AT,
    interpreted_binding,
)


def _evaluate(*interpretations, version=None):
    return evaluate_evidence_sufficiency(
        version or requirement_version(),
        requirement_key(),
        tuple(interpretations),
        effective_at=ASSESSMENT_EFFECTIVE_AT,
        known_at=ASSESSMENT_KNOWN_AT,
    )


def _stale_and_unavailable():
    return (
        interpreted_binding(
            1,
            basis_at=ASSESSMENT_EFFECTIVE_AT - timedelta(minutes=3),
        ),
        interpreted_binding(
            2,
            availability=EvidenceAvailability.UNAVAILABLE,
            materially_used=False,
        ),
    )


@pytest.mark.parametrize(
    ("interpretations", "expected", "expected_result"),
    [
        (
            (interpreted_binding(),),
            EvidenceRequirementDisposition.SATISFIED,
            EvidenceSufficiencyResult.SUFFICIENT,
        ),
        (
            (),
            EvidenceRequirementDisposition.MISSING,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
        (
            (interpreted_binding(role=EvidenceRole.CONTEXTUAL),),
            EvidenceRequirementDisposition.MISSING,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
        (
            (interpreted_binding(materially_used=False),),
            EvidenceRequirementDisposition.MISSING,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
        (
            (
                interpreted_binding(
                    availability=EvidenceAvailability.UNAVAILABLE,
                    materially_used=False,
                ),
            ),
            EvidenceRequirementDisposition.UNAVAILABLE,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
        (
            (
                interpreted_binding(
                    availability=EvidenceAvailability.UNKNOWN,
                    materially_used=False,
                ),
            ),
            EvidenceRequirementDisposition.UNKNOWN,
            EvidenceSufficiencyResult.INDETERMINATE,
        ),
        (
            (
                interpreted_binding(
                    basis_at=ASSESSMENT_EFFECTIVE_AT - timedelta(minutes=3)
                ),
            ),
            EvidenceRequirementDisposition.STALE,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
        (
            (
                interpreted_binding(
                    basis_at=ASSESSMENT_EFFECTIVE_AT + timedelta(microseconds=1)
                ),
            ),
            EvidenceRequirementDisposition.UNKNOWN,
            EvidenceSufficiencyResult.INDETERMINATE,
        ),
        (
            (interpreted_binding(state=EvidenceBindingInterpretationState.DISPUTED),),
            EvidenceRequirementDisposition.DISPUTED,
            EvidenceSufficiencyResult.INDETERMINATE,
        ),
        (
            (interpreted_binding(state=EvidenceBindingInterpretationState.CONTESTED),),
            EvidenceRequirementDisposition.CONTESTED,
            EvidenceSufficiencyResult.INDETERMINATE,
        ),
        (
            (interpreted_binding(state=EvidenceBindingInterpretationState.WITHDRAWN),),
            EvidenceRequirementDisposition.MISSING,
            EvidenceSufficiencyResult.INSUFFICIENT,
        ),
    ],
)
def test_evaluator_derives_every_disposition_without_caller_input(
    interpretations,
    expected,
    expected_result,
) -> None:
    evaluation = _evaluate(*interpretations)

    assert evaluation.requirement_assessments[0].disposition is expected
    assert evaluation.result is expected_result


def test_threshold_counts_distinct_observations_not_binding_roots() -> None:
    version = requirement_version(minimum_distinct_observations=2)
    first = interpreted_binding(1, observation_ordinal=9)
    duplicate = interpreted_binding(2, observation_ordinal=9)

    assessment = _evaluate(first, duplicate, version=version).requirement_assessments[0]

    assert assessment.disposition is EvidenceRequirementDisposition.MISSING
    assert assessment.counted_observation_ids == frozenset(
        {first.binding.observation_id}
    )
    assert {proof.binding_id for proof in assessment.binding_proofs} == {
        first.binding.binding_id,
        duplicate.binding.binding_id,
    }


def test_disposition_precedence_uses_unresolved_then_stale_then_unavailable() -> None:
    version = requirement_version(minimum_distinct_observations=3)
    contributor = interpreted_binding(5)
    stale, unavailable = _stale_and_unavailable()
    disputed = interpreted_binding(
        3,
        state=EvidenceBindingInterpretationState.DISPUTED,
    )
    contested = interpreted_binding(
        4,
        state=EvidenceBindingInterpretationState.CONTESTED,
    )

    disposition = (
        _evaluate(
            contributor,
            stale,
            unavailable,
            disputed,
            contested,
            version=version,
        )
        .requirement_assessments[0]
        .disposition
    )

    assert disposition is EvidenceRequirementDisposition.CONTESTED


def test_unavailable_closes_only_the_gap_left_after_stale_support() -> None:
    version = requirement_version(minimum_distinct_observations=2)
    stale, unavailable = _stale_and_unavailable()

    assessment = _evaluate(
        stale,
        unavailable,
        version=version,
    ).requirement_assessments[0]

    assert assessment.disposition is EvidenceRequirementDisposition.UNAVAILABLE


def test_proof_preserves_typed_deficiency_and_exact_freshness_definition() -> None:
    stale = interpreted_binding(basis_at=ASSESSMENT_EFFECTIVE_AT - timedelta(minutes=3))

    proof = _evaluate(stale).requirement_assessments[0].binding_proofs[0]

    assert proof.deficiency_reason is EvidenceRequirementDeficiencyReason.STALE
    assert proof.fact_support == frozenset(
        {stale.binding.binding_id, stale.binding.observation_id}
    )
    assertion = proof.assertion_proofs[0]
    assert isinstance(assertion.freshness_authority, FreshnessRequirementDefinition)
    assert assertion.freshness_authority.maximum_age == timedelta(minutes=2)


def test_not_applicable_and_zero_definition_require_exact_negative_witnesses() -> None:
    not_applicable = requirement_version(
        sufficiency_applicability=(
            SufficiencyRequirementApplicabilityState.NOT_APPLICABLE
        )
    )
    not_applicable_result = _evaluate(
        interpreted_binding(),
        version=not_applicable,
    )
    zero_definition = replace(
        requirement_version(),
        requirements=(requirement_version().requirements[0],),
    )
    zero_result = _evaluate(version=zero_definition)

    row = not_applicable_result.requirement_assessments[0]
    assert row.disposition is EvidenceRequirementDisposition.NOT_APPLICABLE
    assert row.not_applicable_witness is not None
    assert row.binding_proofs == ()
    assert zero_result.result is EvidenceSufficiencyResult.SUFFICIENT
    assert zero_result.no_requirements_witness is not None


def test_binding_without_freshness_rule_preserves_same_version_witness() -> None:
    version = requirement_version()
    without_freshness = replace(version, requirements=(version.requirements[1],))

    proof = (
        _evaluate(
            interpreted_binding(),
            version=without_freshness,
        )
        .requirement_assessments[0]
        .binding_proofs[0]
    )

    assert (
        proof.assertion_proofs[0].freshness_authority.set_id == without_freshness.set_id
    )
    assert (
        proof.assertion_proofs[0].freshness_authority.version_id
        == without_freshness.version_id
    )


def test_aggregate_failure_precedes_indeterminate_and_success() -> None:
    base = requirement_version()
    second = SufficiencyRequirementDefinition(
        EvidenceRequirementId(UUID("00000000-0000-4000-8000-000000000299")),
        MinimumEligibleEvidence(2, frozenset({EvidenceRole.SUPPORTING})),
        SufficiencyRequirementApplicabilityState.REQUIRED,
        "two supporting observations",
    )
    version = replace(base, requirements=(*base.requirements, second))

    result = _evaluate(interpreted_binding(), version=version)

    assert [row.disposition for row in result.requirement_assessments] == [
        EvidenceRequirementDisposition.SATISFIED,
        EvidenceRequirementDisposition.MISSING,
    ]
    assert result.result is EvidenceSufficiencyResult.INSUFFICIENT


def test_late_fact_and_endpoint_mismatch_abort_instead_of_becoming_missing() -> None:
    late = interpreted_binding()
    late = replace(
        late,
        binding=replace(late.binding, recorded_at=ASSESSMENT_KNOWN_AT + timedelta(1)),
    )
    mismatch = interpreted_binding()
    mismatch = replace(
        mismatch,
        subject=EvidenceSubjectReference("market_price", "QQQ"),
    )

    with pytest.raises(InvalidEvidenceSufficiency, match="outside.*boundary"):
        _evaluate(late)
    with pytest.raises(InvalidEvidenceSufficiency, match="does not match"):
        _evaluate(mismatch)


def test_incomplete_interpretation_ancestry_aborts_assessment() -> None:
    interpretation = interpreted_binding()

    with pytest.raises(InvalidEvidenceSufficiency, match="binding root"):
        replace(
            interpretation,
            fact_support=frozenset({interpretation.binding.observation_id}),
        )
