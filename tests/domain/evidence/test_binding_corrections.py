from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.configuration import EvidenceRequirementApplicabilityKey
from polaris.domain.evidence import (
    EvidenceBindingCorrection,
    EvidenceBindingCorrectionHistory,
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceObservationId,
    InvalidEvidenceCorrection,
    InvalidEvidenceCorrectionHistory,
    interpret_evidence_binding,
)
from polaris.domain.evidence.bindings import (
    EvidenceAvailability,
    EvidenceMaterialQualification,
    EvidenceRole,
    InvalidEvidenceBinding,
)
from polaris.domain.evidence.freshness import (
    EvidenceFreshnessEvaluation,
    EvidenceFreshnessResult,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceUse,
)
from tests.sufficiency_support import interpreted_binding

ROOT = interpreted_binding().binding
T = datetime(2026, 9, 29, 14, 5, tzinfo=UTC)
C1 = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000b01"))
C2 = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000b02"))
C3 = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000b03"))


def correction(identity, target, effect, replacement=None, *, minute=2):
    return EvidenceBindingCorrection(
        identity,
        ROOT.binding_id,
        target,
        effect,
        UnknownActorAttribution(),
        EvidenceCorrectionBasis("reviewed binding correction"),
        ROOT.effective_at + timedelta(minutes=minute),
        ROOT.recorded_at + timedelta(minutes=minute),
        replacement,
    )


def test_complete_replacement_and_recursive_retraction_preserve_lineage() -> None:
    replacement = replace(
        ROOT,
        role=EvidenceRole.QUALIFYING,
        availability=EvidenceAvailability.UNKNOWN,
        materially_used=False,
        freshness=replace(ROOT.freshness, result=EvidenceFreshnessResult.STALE),
        material_qualification=EvidenceMaterialQualification("rechecked"),
    )
    revise = correction(
        C1, ROOT.binding_id, EvidenceCorrectionEffect.REVISE, replacement
    )
    retract = correction(C2, C1, EvidenceCorrectionEffect.RETRACT, minute=3)
    history = EvidenceBindingCorrectionHistory(ROOT, (retract, revise))
    before = history.interpret(effective_at=T, known_at=revise.recorded_at)
    after = history.interpret(effective_at=T, known_at=T)
    assert before.state is EvidenceInterpretationState.DETERMINATE
    assert before.assertions == frozenset({replacement})
    assert after.assertions == frozenset({ROOT})
    assert after.fact_support == frozenset({ROOT.binding_id, C1, C2})


def test_fixed_endpoint_changes_and_invalid_usage_fail_closed() -> None:
    other_target = type(ROOT.target)(UUID("00000000-0000-4000-8000-000000000b11"))
    other_scope = ClaimSpecificEvidenceScope(
        ClaimId(UUID("00000000-0000-4000-8000-000000000b12"))
    )

    def matching_freshness(
        key: EvidenceRequirementApplicabilityKey,
    ) -> EvidenceFreshnessEvaluation:
        return replace(
            ROOT.freshness,
            basis=replace(ROOT.freshness.basis, applicability_key=key),
        )

    key = ROOT.freshness.basis.applicability_key

    for replacement in (
        replace(
            ROOT,
            observation_id=EvidenceObservationId(
                UUID("00000000-0000-4000-8000-000000000b10")
            ),
        ),
        replace(
            ROOT,
            target=other_target,
            freshness=matching_freshness(replace(key, target=other_target)),
        ),
        replace(
            ROOT,
            scope=other_scope,
            freshness=matching_freshness(replace(key, scope=other_scope)),
        ),
        replace(
            ROOT,
            evidence_use=EvidenceUse.CHALLENGE_BASIS,
            freshness=matching_freshness(
                replace(key, evidence_use=EvidenceUse.CHALLENGE_BASIS)
            ),
        ),
    ):
        with pytest.raises(InvalidEvidenceCorrectionHistory, match="cannot change"):
            interpret_evidence_binding(
                ROOT,
                corrections=(
                    correction(
                        C1,
                        ROOT.binding_id,
                        EvidenceCorrectionEffect.REVISE,
                        replacement,
                    ),
                ),
                effective_at=T,
                known_at=T,
            )
    with pytest.raises(InvalidEvidenceBinding, match="AVAILABLE"):
        replace(ROOT, availability=EvidenceAvailability.UNKNOWN)


def test_siblings_coalesce_or_contest_without_order_winner() -> None:
    first = correction(
        C1,
        ROOT.binding_id,
        EvidenceCorrectionEffect.REVISE,
        replace(ROOT, role=EvidenceRole.QUALIFYING),
    )
    same = correction(
        C2, ROOT.binding_id, EvidenceCorrectionEffect.REVISE, first.replacement
    )
    other = replace(same, replacement=replace(ROOT, role=EvidenceRole.CONFLICTING))
    equivalent = EvidenceBindingCorrectionHistory(ROOT, (same, first)).interpret(
        effective_at=T, known_at=T
    )
    contested = EvidenceBindingCorrectionHistory(ROOT, (other, first)).interpret(
        effective_at=T, known_at=T
    )
    reverse = EvidenceBindingCorrectionHistory(ROOT, (first, other)).interpret(
        effective_at=T, known_at=T
    )
    assert equivalent.state is EvidenceInterpretationState.DETERMINATE
    assert equivalent.fact_support == frozenset({ROOT.binding_id, C1, C2})
    assert contested == reverse
    assert contested.state is EvidenceInterpretationState.CONTESTED
    withdrawn = correction(C3, ROOT.binding_id, EvidenceCorrectionEffect.RETRACT)
    assert (
        EvidenceBindingCorrectionHistory(ROOT, (withdrawn, first))
        .interpret(effective_at=T, known_at=T)
        .state
        is EvidenceInterpretationState.CONTESTED
    )


def test_missing_correction_ancestry_is_rejected() -> None:
    orphan = correction(C2, C1, EvidenceCorrectionEffect.RETRACT)
    with pytest.raises(
        InvalidEvidenceCorrectionHistory, match="complete target ancestry"
    ):
        EvidenceBindingCorrectionHistory(ROOT, (orphan,)).interpret(
            effective_at=T, known_at=T
        )


def test_replacement_cannot_be_recorded_after_its_correction() -> None:
    future_recorded = replace(ROOT, recorded_at=T + timedelta(days=1))

    with pytest.raises(InvalidEvidenceCorrection, match="recorded after"):
        EvidenceBindingCorrection(
            correction_id=C1,
            root_id=ROOT.binding_id,
            target=ROOT.binding_id,
            effect=EvidenceCorrectionEffect.REVISE,
            attribution=UnknownActorAttribution(),
            basis=EvidenceCorrectionBasis("future assertion"),
            effective_at=ROOT.effective_at,
            recorded_at=ROOT.recorded_at + timedelta(minutes=2),
            replacement=future_recorded,
        )
