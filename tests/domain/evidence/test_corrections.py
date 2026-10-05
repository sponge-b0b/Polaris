from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from polaris.domain.actors import UnknownActorAttribution
from polaris.domain.evidence import (
    EvidenceCorrectionBasis,
    EvidenceCorrectionEffect,
    EvidenceCorrectionId,
    EvidenceInterpretationState,
    EvidenceObservation,
    EvidenceObservationCorrection,
    EvidenceObservationId,
    EvidenceObservationMaterial,
    EvidenceSourceProvenance,
    EvidenceSubjectReference,
    InvalidEvidenceCorrectionHistory,
    interpret_evidence_observation,
)

ROOT_ID = EvidenceObservationId(UUID("00000000-0000-4000-8000-000000000101"))
REVISION_ID = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000102"))
RETRACTION_ID = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000103"))
ROOT_RECORDED_AT = datetime(2026, 9, 29, 13, 2, tzinfo=UTC)


def _observation(value: str = "321.1") -> EvidenceObservation:
    # arid: disable
    # This domain fixture deliberately mirrors the canonical observation shape
    # while retaining independent construction for correction-algebra tests.
    return EvidenceObservation(
        observation_id=ROOT_ID,
        source=EvidenceSourceProvenance(
            "fred",
            "series:CPIAUCSL:2026-08",
            "Federal Reserve Bank of St. Louis / source publisher",
        ),
        subject=EvidenceSubjectReference("US:CPI", "2026-08"),
        observed_at=datetime(2026, 9, 29, 13, 0, tzinfo=UTC),
        acquired_at=datetime(2026, 9, 29, 13, 1, tzinfo=UTC),
        effective_at=datetime(2026, 9, 29, 13, 0, tzinfo=UTC),
        material=EvidenceObservationMaterial(
            retained_representation=f'{{"value": {value}}}'
        ),
    )
    # arid: enable


def _revised_observation(
    root: EvidenceObservation,
    value: str = "321.2",
) -> EvidenceObservation:
    return replace(
        root,
        material=EvidenceObservationMaterial(
            retained_representation=f'{{"value": {value}}}'
        ),
    )


def _correction(
    correction_id: EvidenceCorrectionId,
    target: EvidenceObservationId | EvidenceCorrectionId,
    effect: EvidenceCorrectionEffect,
    basis: str,
    *,
    effective_at: datetime,
    recorded_at: datetime,
    replacement: EvidenceObservation | None = None,
) -> EvidenceObservationCorrection:
    return EvidenceObservationCorrection(
        correction_id=correction_id,
        root_id=ROOT_ID,
        target=target,
        effect=effect,
        attribution=UnknownActorAttribution(),
        basis=EvidenceCorrectionBasis(basis),
        effective_at=effective_at,
        recorded_at=recorded_at,
        replacement=replacement,
    )


def test_retracting_revision_restores_immediately_preceding_observation() -> None:
    # arid: disable
    # The root/revision/retraction chain is intentionally rebuilt in this
    # falsifier so recursive restoration is not coupled to sibling semantics.
    root = _observation()
    revised = _revised_observation(root)
    revision = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "publisher corrected the release",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        replacement=revised,
    )
    retraction = _correction(
        RETRACTION_ID,
        REVISION_ID,
        EvidenceCorrectionEffect.RETRACT,
        "the correction notice was withdrawn",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=2),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=2),
    )
    # arid: enable

    interpretation = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(retraction, revision),
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=3),
        known_at=ROOT_RECORDED_AT + timedelta(minutes=3),
    )

    assert interpretation.state is EvidenceInterpretationState.DETERMINATE
    assert interpretation.assertions == frozenset({root})
    assert interpretation.fact_support == frozenset(
        {ROOT_ID, REVISION_ID, RETRACTION_ID}
    )


def test_correction_vocabulary_and_replacement_shape_are_closed() -> None:
    assert tuple(EvidenceCorrectionEffect) == (
        EvidenceCorrectionEffect.REVISE,
        EvidenceCorrectionEffect.RETRACT,
    )
    root = _observation()

    with pytest.raises(ValueError, match="complete family-specific replacement"):
        EvidenceObservationCorrection(
            correction_id=REVISION_ID,
            root_id=ROOT_ID,
            target=ROOT_ID,
            effect=EvidenceCorrectionEffect.REVISE,
            attribution=UnknownActorAttribution(),
            basis=EvidenceCorrectionBasis("missing replacement"),
            effective_at=ROOT_RECORDED_AT,
            recorded_at=ROOT_RECORDED_AT,
        )
    with pytest.raises(ValueError, match="cannot carry"):
        EvidenceObservationCorrection(
            correction_id=RETRACTION_ID,
            root_id=ROOT_ID,
            target=ROOT_ID,
            effect=EvidenceCorrectionEffect.RETRACT,
            attribution=UnknownActorAttribution(),
            basis=EvidenceCorrectionBasis("invalid replacement"),
            effective_at=ROOT_RECORDED_AT,
            recorded_at=ROOT_RECORDED_AT,
            replacement=root,
        )


def test_historical_inspection_distinguishes_not_known_and_not_effective() -> None:
    root = _observation()

    not_known = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(),
        effective_at=root.observed_at,
        known_at=ROOT_RECORDED_AT - timedelta(microseconds=1),
    )
    not_effective = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(),
        effective_at=root.observed_at - timedelta(microseconds=1),
        known_at=ROOT_RECORDED_AT,
    )

    assert not_known.state is EvidenceInterpretationState.NOT_KNOWN
    assert not_known.assertions == frozenset()
    assert not_effective.state is EvidenceInterpretationState.NOT_EFFECTIVE
    assert not_effective.assertions == frozenset()


def test_revision_correcting_future_effective_time_retains_root_support() -> None:
    root = replace(
        _observation(),
        effective_at=ROOT_RECORDED_AT + timedelta(days=2),
    )
    revised = replace(
        root,
        effective_at=ROOT_RECORDED_AT - timedelta(minutes=1),
    )
    # This temporal-support falsifier constructs its own lineage branch.
    # arid: disable
    revision = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "correct misrecorded effective time",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        replacement=revised,
    )
    # arid: enable
    cutoff = ROOT_RECORDED_AT + timedelta(minutes=2)

    original = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(),
        effective_at=cutoff,
        known_at=cutoff,
    )
    corrected = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(revision,),
        effective_at=cutoff,
        known_at=cutoff,
    )

    assert original.state is EvidenceInterpretationState.NOT_EFFECTIVE
    assert corrected.state is EvidenceInterpretationState.DETERMINATE
    assert corrected.assertions == frozenset({revised})
    assert corrected.fact_support == frozenset({ROOT_ID, REVISION_ID})


def test_retracting_known_future_revision_retains_target_lineage_support() -> None:
    root = _observation()
    future_revision = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "future effective notice",
        effective_at=ROOT_RECORDED_AT + timedelta(days=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        replacement=_revised_observation(root),
    )
    current_retraction = _correction(
        RETRACTION_ID,
        REVISION_ID,
        EvidenceCorrectionEffect.RETRACT,
        "notice withdrawn before taking effect",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=2),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=2),
    )

    interpreted = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(current_retraction, future_revision),
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=3),
        known_at=ROOT_RECORDED_AT + timedelta(minutes=3),
    )

    assert interpreted.state is EvidenceInterpretationState.DETERMINATE
    assert interpreted.assertions == frozenset({root})
    assert interpreted.fact_support == frozenset({ROOT_ID, REVISION_ID, RETRACTION_ID})


def test_siblings_coalesce_equivalent_assertions_and_contest_incompatible_ones() -> (
    None
):
    root = _observation()
    corrected = _revised_observation(root)
    incompatible = _revised_observation(root, "321.3")
    first = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "first publisher notice",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        replacement=corrected,
    )
    second_id = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000104"))
    equivalent = replace(
        first,
        correction_id=second_id,
        basis=EvidenceCorrectionBasis("independent equivalent notice"),
    )
    cutoff = ROOT_RECORDED_AT + timedelta(minutes=4)

    coalesced = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(equivalent, first),
        effective_at=cutoff,
        known_at=cutoff,
    )
    contested = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(
            replace(equivalent, replacement=incompatible),
            first,
        ),
        effective_at=cutoff,
        known_at=cutoff,
    )

    assert coalesced.state is EvidenceInterpretationState.DETERMINATE
    assert coalesced.assertions == frozenset({corrected})
    assert coalesced.fact_support == frozenset({ROOT_ID, REVISION_ID, second_id})
    assert contested.state is EvidenceInterpretationState.CONTESTED
    assert contested.assertions == frozenset({corrected, incompatible})


def test_positive_and_withdrawal_siblings_are_contested_without_ordering_winner() -> (
    None
):
    # arid: disable
    # This sibling conflict is independently constructed to prove that input
    # ordering cannot turn either correction into an implicit winner.
    root = _observation()
    revised = _revised_observation(root)
    revision = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "revision",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=3),
        replacement=revised,
    )
    withdrawal = _correction(
        RETRACTION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.RETRACT,
        "withdrawal",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=2),
    )
    # arid: enable
    cutoff = ROOT_RECORDED_AT + timedelta(minutes=4)

    forward = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(revision, withdrawal),
        effective_at=cutoff,
        known_at=cutoff,
    )
    reverse = interpret_evidence_observation(
        root,
        root_recorded_at=ROOT_RECORDED_AT,
        corrections=(withdrawal, revision),
        effective_at=cutoff,
        known_at=cutoff,
    )

    assert forward == reverse
    assert forward.state is EvidenceInterpretationState.CONTESTED
    assert forward.assertions == frozenset({revised})


def test_missing_ancestry_and_cycles_fail_closed() -> None:
    root = _observation()
    first_id = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000111"))
    second_id = EvidenceCorrectionId(UUID("00000000-0000-4000-8000-000000000112"))
    missing = _correction(
        first_id,
        second_id,
        EvidenceCorrectionEffect.RETRACT,
        "missing ancestry",
        effective_at=ROOT_RECORDED_AT + timedelta(minutes=1),
        recorded_at=ROOT_RECORDED_AT + timedelta(minutes=2),
    )
    with pytest.raises(InvalidEvidenceCorrectionHistory, match="complete target"):
        interpret_evidence_observation(
            root,
            root_recorded_at=ROOT_RECORDED_AT,
            corrections=(missing,),
            effective_at=ROOT_RECORDED_AT + timedelta(minutes=3),
            known_at=ROOT_RECORDED_AT + timedelta(minutes=3),
        )

    cycle = (
        replace(missing, target=second_id),
        replace(
            missing,
            correction_id=second_id,
            target=first_id,
            basis=EvidenceCorrectionBasis("cycle"),
        ),
    )
    with pytest.raises(InvalidEvidenceCorrectionHistory, match="acyclic"):
        interpret_evidence_observation(
            root,
            root_recorded_at=ROOT_RECORDED_AT,
            corrections=cycle,
            effective_at=ROOT_RECORDED_AT + timedelta(minutes=3),
            known_at=ROOT_RECORDED_AT + timedelta(minutes=3),
        )


def test_correction_cannot_target_later_recorded_history() -> None:
    root = _observation()
    recorded_at = ROOT_RECORDED_AT + timedelta(minutes=1)
    revision = _correction(
        REVISION_ID,
        ROOT_ID,
        EvidenceCorrectionEffect.REVISE,
        "revision",
        effective_at=recorded_at,
        recorded_at=recorded_at,
        replacement=_revised_observation(root),
    )
    earlier_recorded_child = _correction(
        RETRACTION_ID,
        REVISION_ID,
        EvidenceCorrectionEffect.RETRACT,
        "temporally impossible child",
        effective_at=recorded_at,
        recorded_at=recorded_at - timedelta(microseconds=1),
    )

    with pytest.raises(InvalidEvidenceCorrectionHistory, match="later-recorded"):
        interpret_evidence_observation(
            root,
            root_recorded_at=ROOT_RECORDED_AT,
            corrections=(earlier_recorded_child, revision),
            effective_at=recorded_at,
            known_at=recorded_at,
        )
