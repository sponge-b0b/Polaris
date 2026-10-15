from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from uuid import UUID

import pytest

from polaris.domain.actors import (
    ActorId,
    KnownActorAttribution,
    UnknownActorAttribution,
)
from polaris.domain.evidence import (
    EvidenceAssessmentCorrection,
    EvidenceAssessmentCorrectionHistory,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    InvalidEvidenceCorrectionHistory,
)
from tests.configuration_support import SECOND_VERSION_ID, requirement_version
from tests.sufficiency_support import derived_assessment


def _correction(
    ordinal: int,
    target,
    *,
    effect: EvidenceCorrectionEffect = EvidenceCorrectionEffect.REVISE,
    replacement=None,
) -> EvidenceAssessmentCorrection:
    root = derived_assessment()
    return EvidenceAssessmentCorrection(
        correction_id=EvidenceCorrectionId(
            UUID(f"30000000-0000-4000-8000-{ordinal:012x}")
        ),
        root_id=root.assessment_id,
        target=target,
        effect=effect,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis("assessment record correction"),
        effective_at=root.effective_at,
        recorded_at=root.recorded_at + timedelta(minutes=ordinal),
        replacement=(
            root
            if replacement is None and effect is EvidenceCorrectionEffect.REVISE
            else replacement
        ),
    )


def test_assessment_revision_retraction_restores_preceding_branch() -> None:
    root = derived_assessment()
    revised = _correction(1, root.assessment_id)
    withdrawn = _correction(
        2,
        revised.correction_id,
        effect=EvidenceCorrectionEffect.RETRACT,
    )
    history = EvidenceAssessmentCorrectionHistory(root, (withdrawn, revised))

    interpretation = history.interpret(
        effective_at=root.effective_at,
        known_at=withdrawn.recorded_at,
    )

    assert interpretation.state is EvidenceInterpretationState.DETERMINATE
    assert interpretation.assertions == frozenset({root})
    assert interpretation.fact_support == frozenset(
        {root.assessment_id, revised.correction_id, withdrawn.correction_id}
    )


def test_equivalent_siblings_coalesce_and_incompatible_siblings_contest() -> None:
    root = derived_assessment()
    first = _correction(1, root.assessment_id)
    second = _correction(2, root.assessment_id)
    equivalent = EvidenceAssessmentCorrectionHistory(root, (second, first)).interpret(
        effective_at=root.effective_at,
        known_at=second.recorded_at,
    )
    assert equivalent.state is EvidenceInterpretationState.DETERMINATE
    assert equivalent.assertions == frozenset({root})
    assert {first.correction_id, second.correction_id} <= equivalent.fact_support

    changed = replace(
        root,
        attribution=KnownActorAttribution(
            ActorId(UUID("40000000-0000-4000-8000-000000000001"))
        ),
    )
    competing = _correction(3, root.assessment_id, replacement=changed)
    contested = EvidenceAssessmentCorrectionHistory(root, (first, competing)).interpret(
        effective_at=root.effective_at,
        known_at=competing.recorded_at,
    )
    assert contested.state is EvidenceInterpretationState.CONTESTED
    assert contested.assertions == frozenset({root, changed})


def test_assessment_replacement_cannot_change_boundary_or_requirement_version() -> None:
    root = derived_assessment(interpretations=())
    second_version = replace(
        derived_assessment(
            interpretations=(), version=requirement_version(SECOND_VERSION_ID)
        ),
        assessment_id=root.assessment_id,
    )
    for replacement in (
        replace(root, effective_at=root.effective_at + timedelta(minutes=1)),
        second_version,
    ):
        correction = _correction(1, root.assessment_id, replacement=replacement)
        with pytest.raises(InvalidEvidenceCorrectionHistory):
            EvidenceAssessmentCorrectionHistory(root, (correction,)).interpret(
                effective_at=root.effective_at,
                known_at=correction.recorded_at,
            )


def test_assessment_correction_requires_same_root_acyclic_ancestry() -> None:
    root = derived_assessment()
    missing = _correction(
        1,
        EvidenceCorrectionId(UUID("30000000-0000-4000-8000-000000000099")),
    )
    with pytest.raises(InvalidEvidenceCorrectionHistory):
        EvidenceAssessmentCorrectionHistory(root, (missing,)).interpret(
            effective_at=root.effective_at,
            known_at=missing.recorded_at,
        )
    other = derived_assessment(2)
    wrong = replace(
        _correction(1, root.assessment_id),
        root_id=other.assessment_id,
        target=other.assessment_id,
        replacement=other,
    )
    with pytest.raises(InvalidEvidenceCorrectionHistory):
        EvidenceAssessmentCorrectionHistory(root, (wrong,)).interpret(
            effective_at=root.effective_at,
            known_at=wrong.recorded_at,
        )
    first = _correction(3, root.assessment_id)
    second = _correction(4, first.correction_id)
    cycle = replace(first, target=second.correction_id)
    with pytest.raises(InvalidEvidenceCorrectionHistory):
        EvidenceAssessmentCorrectionHistory(root, (cycle, second)).interpret(
            effective_at=root.effective_at,
            known_at=second.recorded_at,
        )
