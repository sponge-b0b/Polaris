from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from polaris.domain.decisions import (
    ActorId,
    ContestedActorAttribution,
    ContestedDecisionLifecycleInterpretation,
    DecisionApplicability,
    DecisionContinuity,
    DecisionDeferred,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrected,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionLifecycleInterpretationContested,
    DecisionLifecycleNotYetEffective,
    DecisionLifecycleSequence,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionNotKnownAtCutoff,
    DecisionScope,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    DeterminateDecisionLifecycleInterpretation,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionLifecycleCorrection,
    InvalidDecisionTransition,
    InvestmentDecisionId,
    KnownActorAttribution,
    NotYetEffectiveDecisionLifecycleInterpretation,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnknownActorAttribution,
    UnsupportedDecisionNeedBasis,
    correct_decision_lifecycle,
    defer_decision,
    externally_resolve_decision,
    initiate_decision,
    reconstruct_decision,
    resume_decision_work,
    substantively_resolve_decision,
    withdraw_decision_work,
)

ORIGIN = datetime(2026, 9, 8, 10, tzinfo=UTC)
OPERATIVE = DecisionApplicability.OPERATIVE
UNRESOLVED = DecisionLifecycleDisposition.UNRESOLVED
EXTERNAL = DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
SUBSTANTIVE = DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
UNSUPPORTED = DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
QUALIFY = DecisionLifecycleCorrectionEffect.QUALIFY
DISCONFIRM = DecisionLifecycleCorrectionEffect.DISCONFIRM


def at(minutes):
    return ORIGIN + timedelta(minutes=minutes)


def mutation(recorded, effective=None):
    return DecisionMutationContext(
        fact_id=DecisionLifecycleFactId(uuid4()),
        operation_id=OperationId(uuid4()),
        actor_attribution=KnownActorAttribution(ActorId(uuid4())),
        trigger=TriggerProvenance(
            TriggerKind.EXTERNAL_OBSERVATION, f"observation-{recorded}"
        ),
        technical_provenance=TechnicalProvenance(
            [TechnicalReference(TechnicalReferenceKind.REQUEST, str(uuid4()))]
        ),
        recorded_at=at(recorded),
        effective_at=at(recorded if effective is None else effective),
    )


# duplicate-code: this lifecycle correction suite keeps its own Decision builder because its recording/effective-time defaults are part of the correction proof DSL; sharing the relationship-suite builder would couple independent temporal fixtures.
# arid: disable
def initiate(*, recorded=0, effective=0):
    context = mutation(recorded, effective)
    need = DecisionNeed(
        need_id=DecisionNeedId(uuid4()),
        statement="Whether to change exposure",
        effective_at=at(effective),
        recorded_at=at(recorded),
        operation_id=context.operation_id,
        actor_attribution=context.actor_attribution,
        trigger=context.trigger,
    )
    return initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("Whether to change exposure"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=at(recorded),
        ),
        mutation=context,
    )
# arid: enable


def human(effect):
    return TrustedHumanInvestmentDecisionBasis(str(uuid4()), effect)


def resolve(decision, recorded=10, effective=None, disposition=SUBSTANTIVE):
    if disposition is EXTERNAL:
        return externally_resolve_decision(
            decision,
            basis=ExternalResolutionBasis("circumstances"),
            mutation=mutation(recorded, effective),
        )
    return substantively_resolve_decision(
        decision,
        basis=human(HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING),
        applicability=OPERATIVE,
        mutation=mutation(recorded, effective),
    )


def correct(
    decision,
    target,
    recorded,
    *,
    effective=None,
    disposition=None,
    effect=QUALIFY,
    basis=None,
    applicability=OPERATIVE,
):
    if basis is None:
        if disposition is EXTERNAL:
            basis = ExternalResolutionBasis("external correction support")
        elif disposition is SUBSTANTIVE:
            basis = human(HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING)
        elif disposition is UNSUPPORTED:
            basis = UnsupportedDecisionNeedBasis("Need determination unsupported")
    return correct_decision_lifecycle(
        decision,
        target_fact_id=target.metadata.fact_id,
        effect=effect,
        correction_basis=DecisionLifecycleCorrectionBasis("new supported knowledge"),
        replacement_disposition=disposition,
        replacement_basis=basis,
        mutation=mutation(recorded, effective),
        applicability=applicability,
    )


def query(decision, effective, known=None, applicability=OPERATIVE):
    return decision.effective_at(
        at(effective),
        known_at=at(effective if known is None else known),
        applicability=applicability,
    )


def assert_result(decision, disposition, *support):
    result = decision.lifecycle_interpretation
    assert isinstance(result, DeterminateDecisionLifecycleInterpretation)
    assert result.disposition is disposition
    assert result.support_fact_ids == frozenset(f.metadata.fact_id for f in support)


def assert_contested(decision, *support):
    result = decision.lifecycle_interpretation
    assert isinstance(result, ContestedDecisionLifecycleInterpretation)
    assert result.support_fact_ids == frozenset(f.metadata.fact_id for f in support)
    assert decision.work_posture is None
    with pytest.raises(DecisionLifecycleInterpretationContested):
        _ = decision.disposition


def rebuild(history, observed=100):
    return reconstruct_decision(
        history, observed_at=at(observed), applicability=OPERATIVE
    )


def test_absence_future_initiation_and_explicit_boundaries():
    decision = initiate(effective=60)
    with pytest.raises(DecisionNotKnownAtCutoff):
        query(decision, -30)
    before = query(decision, 30)
    result = before.lifecycle_interpretation
    assert isinstance(result, NotYetEffectiveDecisionLifecycleInterpretation)
    assert result.kind == "NOT_YET_EFFECTIVE"
    assert (result.effective_at, result.known_at) == (at(30), at(30))
    assert not hasattr(result, "disposition")
    assert not hasattr(result, "support_fact_ids")
    assert before.work_posture is None
    assert before.history == decision.history
    with pytest.raises(DecisionLifecycleNotYetEffective):
        _ = before.disposition
    with pytest.raises(DecisionLifecycleNotYetEffective):
        defer_decision(
            before,
            basis=human(HumanInvestmentDecisionEffect.DEFERRING),
            applicability=OPERATIVE,
            mutation=mutation(30),
        )
    assert_result(query(decision, 60), UNRESOLVED, decision.history[0])
    assert query(decision, 60).version == decision.version == DecisionVersion(1)


def test_backdated_initiation_qualification_changes_only_later_knowledge():
    decision = initiate(effective=60)
    original = decision.history[0]
    corrected = correct(decision, original, 120, effective=-60, disposition=UNRESOLVED)
    fact = corrected.history[-1]
    assert isinstance(
        query(corrected, 30).lifecycle_interpretation,
        NotYetEffectiveDecisionLifecycleInterpretation,
    )
    assert_result(query(corrected, 30, 150), UNRESOLVED, fact)
    assert corrected.version == DecisionVersion(2)
    assert corrected.need == decision.need
    assert corrected.history[0] == original


@pytest.mark.parametrize("root_kind", [UNRESOLVED, SUBSTANTIVE, EXTERNAL])
@pytest.mark.parametrize("replacement", [UNRESOLVED, SUBSTANTIVE, EXTERNAL])
def test_qualification_complete_replacement_on_all_eligible_roots(
    root_kind, replacement
):
    decision = initiate()
    if root_kind is not UNRESOLVED:
        decision = resolve(decision, disposition=root_kind)
    root = decision.history[-1]
    corrected = correct(decision, root, 20, effective=5, disposition=replacement)
    correction = corrected.history[-1]
    assert_result(corrected, replacement, correction)
    assert corrected.history[:-1] == decision.history
    assert correction.metadata.sequence.value == len(corrected.history)
    assert correction.metadata.fact_id not in {
        f.metadata.fact_id for f in decision.history
    }
    assert correction.correction_basis.reference
    assert correction.metadata.actor_attribution != root.metadata.actor_attribution
    assert correction.metadata.trigger != root.metadata.trigger
    assert (
        correction.metadata.technical_provenance != root.metadata.technical_provenance
    )
    assert corrected.need == decision.need
    with pytest.raises(FrozenInstanceError):
        correction.target_fact_id = DecisionLifecycleFactId(uuid4())


def test_restore_positive_and_withdrawal_recursively_without_defeated_ancestry():
    decision = resolve(initiate())
    initial, root = decision.history
    decision = correct(decision, root, 20, effective=5, disposition=EXTERNAL)
    c1 = decision.history[-1]
    decision = correct(decision, c1, 30, effect=DISCONFIRM)
    c2 = decision.history[-1]
    assert_result(decision, SUBSTANTIVE, root, c2)
    decision = correct(decision, c2, 40, effect=DISCONFIRM)
    c3 = decision.history[-1]
    assert_result(decision, EXTERNAL, c1, c3)
    # Independent chain directly withdraws the resolution, then restores it.
    decision = resolve(initiate())
    initial, root = decision.history
    decision = correct(decision, root, 20, effect=DISCONFIRM)
    withdrawal = decision.history[-1]
    assert_result(decision, UNRESOLVED, initial, withdrawal)
    decision = correct(decision, withdrawal, 30, effect=DISCONFIRM)
    restore = decision.history[-1]
    assert_result(decision, SUBSTANTIVE, root, restore)
    decision = correct(decision, restore, 40, effect=DISCONFIRM)
    restore_withdrawal = decision.history[-1]
    assert_result(decision, UNRESOLVED, initial, withdrawal, restore_withdrawal)
    decision = correct(decision, restore_withdrawal, 50, disposition=EXTERNAL)
    assert_result(decision, EXTERNAL, decision.history[-1])


@pytest.mark.parametrize(
    "second_disposition,second_effect",
    [(EXTERNAL, QUALIFY), (SUBSTANTIVE, QUALIFY), (None, DISCONFIRM)],
)
def test_siblings_coalesce_or_contest_without_latest_write_winner(
    second_disposition, second_effect
):
    decision = resolve(initiate())
    root = decision.history[-1]
    decision = correct(decision, root, 20, effective=5, disposition=EXTERNAL)
    c1 = decision.history[-1]
    decision = correct(
        decision,
        root,
        30,
        effective=5,
        disposition=second_disposition,
        effect=second_effect,
    )
    c2 = decision.history[-1]
    if second_disposition is EXTERNAL:
        assert_result(decision, EXTERNAL, c1, c2)
    else:
        assert_contested(decision, c1, c2)
        with pytest.raises(DecisionLifecycleInterpretationContested):
            resolve(decision, recorded=40)
    assert decision.version == DecisionVersion(4)
    # Defeating one sibling restores its own root, never erases the other sibling.
    decision = correct(decision, c2, 40, effect=DISCONFIRM)
    assert_contested(decision, c1, root, decision.history[-1])


def test_nested_equivalent_restoration_preserves_all_sibling_support():
    decision = resolve(initiate())
    root = decision.history[-1]
    decision = correct(decision, root, 20, effective=10, disposition=SUBSTANTIVE)
    c1 = decision.history[-1]
    decision = correct(decision, root, 30, effective=10, disposition=SUBSTANTIVE)
    c2 = decision.history[-1]
    decision = correct(decision, c1, 40, effect=DISCONFIRM)
    assert_result(decision, SUBSTANTIVE, root, c2, decision.history[-1])


@pytest.mark.parametrize("descendant_effect", [QUALIFY, DISCONFIRM])
def test_descendant_activates_independently_of_future_ancestor(descendant_effect):
    decision = resolve(initiate())
    root = decision.history[-1]
    decision = correct(decision, root, 20, effective=100, disposition=EXTERNAL)
    future = decision.history[-1]
    assert_result(decision, SUBSTANTIVE, root)
    assert decision.version == DecisionVersion(2)
    decision = correct(
        decision,
        future,
        30,
        effective=30,
        effect=descendant_effect,
        disposition=UNRESOLVED if descendant_effect is QUALIFY else None,
    )
    child = decision.history[-1]
    if descendant_effect is QUALIFY:
        assert_result(decision, UNRESOLVED, child)
        assert_result(query(decision, 100), UNRESOLVED, child)
    else:
        assert_result(decision, SUBSTANTIVE, root)
        assert_result(query(decision, 100), SUBSTANTIVE, root, child)
        assert decision.version == DecisionVersion(2)
    assert query(decision, 100).version == decision.version
    assert query(decision, 25).history == decision.history[:-1]
    with pytest.raises(InvalidDecisionLifecycleCorrection):
        rebuild(
            (
                decision.history[0],
                root,
                replace(
                    child,
                    metadata=replace(
                        child.metadata, sequence=DecisionLifecycleSequence(3)
                    ),
                ),
            )
        )


def test_future_sibling_does_not_compete_with_present_withdrawal():
    decision = resolve(initiate())
    initial, root = decision.history
    decision = correct(decision, root, 20, effective=100, disposition=EXTERNAL)
    future = decision.history[-1]
    decision = correct(decision, root, 30, effect=DISCONFIRM)
    withdrawal = decision.history[-1]
    assert_result(decision, UNRESOLVED, initial, withdrawal)
    assert_contested(query(decision, 100), future, withdrawal)
    assert query(decision, 100).version == decision.version


@pytest.mark.parametrize(
    "first_time,second_time,first_disposition,second_disposition,expected",
    [
        (0, 10, UNRESOLVED, UNRESOLVED, UNRESOLVED),
        (10, 10, UNRESOLVED, UNRESOLVED, UNRESOLVED),
        (0, 10, UNRESOLVED, EXTERNAL, EXTERNAL),
        (10, 10, EXTERNAL, EXTERNAL, EXTERNAL),
        (5, 10, EXTERNAL, EXTERNAL, None),
        (10, 10, SUBSTANTIVE, EXTERNAL, None),
        (5, 10, EXTERNAL, UNRESOLVED, None),
        (10, 10, EXTERNAL, UNRESOLVED, None),
        (10, 10, UNRESOLVED, EXTERNAL, EXTERNAL),
        (10, 10, UNSUPPORTED, EXTERNAL, None),
    ],
)
def test_cross_root_compatibility_and_exact_support(
    first_time, second_time, first_disposition, second_disposition, expected
):
    decision = resolve(initiate())
    initial, root = decision.history
    decision = correct(
        decision, initial, 20, effective=first_time, disposition=first_disposition
    )
    first = decision.history[-1]
    decision = correct(
        decision, root, 30, effective=second_time, disposition=second_disposition
    )
    second = decision.history[-1]
    if expected is None:
        assert_contested(decision, first, second)
    elif first_time == second_time and first_disposition is second_disposition:
        assert_result(decision, expected, first, second)
    else:
        assert_result(decision, expected, second)


@pytest.mark.parametrize(
    "posture",
    [
        DecisionWorkPosture.DEFERRED,
        DecisionWorkPosture.WITHDRAWN,
        DecisionWorkPosture.ACTIVE,
    ],
)
def test_corrected_resolution_restores_independent_work_history(posture):
    decision = defer_decision(
        initiate(),
        basis=human(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=OPERATIVE,
        mutation=mutation(2),
    )
    if posture is DecisionWorkPosture.WITHDRAWN:
        decision = withdraw_decision_work(
            decision,
            basis=DecisionWorkControlBasis("stop work"),
            applicability=OPERATIVE,
            mutation=mutation(3),
        )
    elif posture is DecisionWorkPosture.ACTIVE:
        decision = resume_decision_work(
            decision,
            basis=DecisionWorkControlBasis("resume"),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=OPERATIVE,
            mutation=mutation(3),
        )
    decision = resolve(decision)
    root = decision.history[-1]
    decision = correct(decision, root, 20, effect=DISCONFIRM)
    assert decision.disposition is UNRESOLVED
    assert decision.work_posture is posture
    assert len(decision.history) == (
        4 if posture is DecisionWorkPosture.DEFERRED else 5
    )


# duplicate-code: these adjacent tests intentionally spell out different temporal/posture histories; a shared command-sequence fixture would hide whether backdating or effective-time ordering is the property under proof.
# arid: disable
def test_backdated_correction_preserves_historical_admission_and_attribution():
    decision = defer_decision(
        initiate(),
        basis=human(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=OPERATIVE,
        mutation=mutation(5),
    )
    initial, deferral = decision.history
    decision = correct(decision, initial, 30, effective=3, disposition=EXTERNAL)
    assert query(decision, 5).work_posture is DecisionWorkPosture.DEFERRED
    assert query(decision, 5, 30).work_posture is None
    assert decision.history[1] == deferral
    assert rebuild(decision.history).history == decision.history


def test_posture_orders_effective_time_then_sequence_separately_from_admission():
    decision = defer_decision(
        initiate(),
        basis=human(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=OPERATIVE,
        mutation=mutation(10, 20),
    )
    decision = defer_decision(
        decision,
        basis=human(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=OPERATIVE,
        mutation=mutation(30, 5),
    )
    decision = withdraw_decision_work(
        decision,
        basis=DecisionWorkControlBasis("withdraw"),
        applicability=OPERATIVE,
        mutation=mutation(40, 15),
    )
    # Latest sequence is withdrawal, but the later effective Deferral governs.
    assert decision.work_posture is DecisionWorkPosture.DEFERRED
    decision = withdraw_decision_work(
        decision,
        basis=DecisionWorkControlBasis("later withdrawal"),
        applicability=OPERATIVE,
        mutation=mutation(50, 20),
    )
    assert decision.work_posture is DecisionWorkPosture.WITHDRAWN
# arid: enable


def test_stale_view_cannot_authorize_after_clock_crosses_future_resolution():
    decision = resolve(initiate(), recorded=10, effective=20)
    assert decision.disposition is UNRESOLVED
    with pytest.raises(InvalidDecisionTransition):
        defer_decision(
            decision,
            basis=human(HumanInvestmentDecisionEffect.DEFERRING),
            applicability=OPERATIVE,
            mutation=mutation(30),
        )
    assert query(decision, 30).disposition is SUBSTANTIVE
    assert query(decision, 30).version == decision.version


def test_ordinary_effective_prerequisites_and_known_future_incompatibility():
    decision = initiate(effective=10)
    with pytest.raises(DecisionLifecycleNotYetEffective):
        resolve(decision, recorded=20, effective=5)
    decision = resolve(initiate(), recorded=10, effective=100)
    with pytest.raises(InvalidDecisionTransition, match="incompatible"):
        resolve(decision, recorded=20, effective=50, disposition=EXTERNAL)


def test_equal_recorded_time_prefix_and_decreasing_time_rejection():
    decision = resolve(initiate(), recorded=0, effective=0)
    initial, root = decision.history
    decision = correct(decision, root, 0, effective=0, disposition=UNRESOLVED)
    assert_result(decision, UNRESOLVED, initial, decision.history[-1])
    with pytest.raises(InvalidDecisionHistory, match="non-decreasing"):
        rebuild(
            (
                initial,
                replace(root, metadata=replace(root.metadata, recorded_at=at(-1))),
            )
        )
    # A later same-time correction cannot justify an earlier illegal ordinary act.
    bad_deferral = DecisionDeferred(
        replace(
            root.metadata,
            fact_id=DecisionLifecycleFactId(uuid4()),
            sequence=DecisionLifecycleSequence(3),
            decision_version=DecisionVersion(3),
        ),
        human(HumanInvestmentDecisionEffect.DEFERRING),
    )
    correction = replace(
        decision.history[-1],
        metadata=replace(
            decision.history[-1].metadata,
            sequence=DecisionLifecycleSequence(4),
            decision_version=DecisionVersion(4),
        ),
    )
    with pytest.raises(InvalidDecisionHistory, match="resolved"):
        rebuild((initial, root, bad_deferral, correction))


@pytest.mark.parametrize("applicability", list(DecisionApplicability))
def test_correction_bypasses_work_applicability_gate(applicability):
    decision = resolve(initiate())
    root = decision.history[-1]
    decision = correct(
        decision, root, 20, effect=DISCONFIRM, applicability=applicability
    )
    assert decision.disposition is UNRESOLVED
    assert decision.work_posture is (
        DecisionWorkPosture.ACTIVE if applicability is OPERATIVE else None
    )


def test_historical_only_correction_retains_version_and_current_terminal_support():
    decision = resolve(initiate())
    initial, root = decision.history
    decision = correct(decision, initial, 20, effective=5, disposition=UNRESOLVED)
    assert_result(decision, SUBSTANTIVE, root)
    assert decision.version == DecisionVersion(2)
    assert decision.history[-1].metadata.sequence == DecisionLifecycleSequence(3)
    assert_result(query(decision, 6, 20), UNRESOLVED, decision.history[-1])


def test_distinct_equivalent_acts_append_and_support_only_changes_advance_version():
    decision = initiate()
    initial = decision.history[0]
    decision = correct(decision, initial, 10, effective=0, disposition=UNRESOLVED)
    first = decision.history[-1]
    decision = correct(decision, initial, 20, effective=0, disposition=UNRESOLVED)
    second = decision.history[-1]
    assert_result(decision, UNRESOLVED, first, second)
    assert decision.version == DecisionVersion(3)
    assert first.metadata.operation_id != second.metadata.operation_id
    assert rebuild(decision.history).history == decision.history
    with pytest.raises(InvalidDecisionHistory, match="version"):
        rebuild(
            (
                *decision.history[:-1],
                replace(
                    second,
                    metadata=replace(
                        second.metadata, decision_version=DecisionVersion(2)
                    ),
                ),
            )
        )


def test_as_known_at_equivalence_and_timezone_instant_equality():
    decision = resolve(initiate())
    decision = correct(
        decision, decision.history[-1], 20, effective=5, disposition=EXTERNAL
    )
    for instant in (0, 5, 10, 19, 20, 30):
        assert decision.as_known_at(at(instant), applicability=OPERATIVE) == query(
            decision, instant
        )
    local = at(30).astimezone(timezone(timedelta(hours=-6)))
    assert decision.as_known_at(local, applicability=OPERATIVE) == query(decision, 30)
    with pytest.raises(ValueError, match="timezone-aware"):
        decision.as_known_at(datetime(2026, 9, 8), applicability=OPERATIVE)


@pytest.mark.parametrize(
    "effect,disposition,basis",
    [
        (DISCONFIRM, UNRESOLVED, None),
        (DISCONFIRM, None, ExternalResolutionBasis("x")),
        (QUALIFY, None, None),
        (QUALIFY, EXTERNAL, None),
        (QUALIFY, UNRESOLVED, ExternalResolutionBasis("x")),
        (
            QUALIFY,
            SUBSTANTIVE,
            TrustedHumanInvestmentDecisionBasis(
                "x", HumanInvestmentDecisionEffect.DEFERRING
            ),
        ),
        (QUALIFY, UNSUPPORTED, ExternalResolutionBasis("x")),
    ],
)
def test_incomplete_or_wrong_purpose_replacements_fail(effect, disposition, basis):
    decision = initiate()
    with pytest.raises((InvalidDecisionBasis, InvalidDecisionLifecycleCorrection)):
        correct_decision_lifecycle(
            decision,
            target_fact_id=decision.history[0].metadata.fact_id,
            correction_basis=DecisionLifecycleCorrectionBasis("why"),
            effect=effect,
            replacement_disposition=disposition,
            replacement_basis=basis,
            mutation=mutation(20),
            applicability=OPERATIVE,
        )


@pytest.mark.parametrize(
    "basis_type", [DecisionLifecycleCorrectionBasis, UnsupportedDecisionNeedBasis]
)
def test_correction_bases_require_nonempty_purpose_specific_reference(basis_type):
    with pytest.raises(InvalidDecisionBasis):
        basis_type(" ")


def test_direct_initiation_disconfirmation_and_unknown_targets_fail():
    decision = initiate()
    with pytest.raises(InvalidDecisionLifecycleCorrection, match="initiation"):
        correct(decision, decision.history[0], 20, effect=DISCONFIRM)
    for identity in (DecisionLifecycleFactId(uuid4()), mutation(20).fact_id):
        with pytest.raises(InvalidDecisionLifecycleCorrection):
            correct_decision_lifecycle(
                decision,
                target_fact_id=identity,
                effect=QUALIFY,
                correction_basis=DecisionLifecycleCorrectionBasis("why"),
                replacement_disposition=UNRESOLVED,
                mutation=mutation(20),
                applicability=OPERATIVE,
            )


@pytest.mark.parametrize("root_disposition", [UNRESOLVED, SUBSTANTIVE, EXTERNAL])
@pytest.mark.parametrize("nested", [False, True])
def test_unsupported_need_eligibility_is_initiation_lineage_only(
    root_disposition, nested
):
    decision = initiate()
    if root_disposition is not UNRESOLVED:
        decision = resolve(decision, disposition=root_disposition)
    root = decision.history[-1]
    if nested:
        decision = correct(decision, root, 20, disposition=UNRESOLVED)
        root = decision.history[-1]
    if root_disposition is UNRESOLVED:
        corrected = correct(decision, root, 30, disposition=UNSUPPORTED)
        assert_result(corrected, UNSUPPORTED, corrected.history[-1])
        assert corrected.need == decision.need
    else:
        with pytest.raises(
            InvalidDecisionLifecycleCorrection, match="initiation lineage"
        ):
            correct(decision, root, 30, disposition=UNSUPPORTED)


# duplicate-code: this explicit fact-kind matrix is the proof surface for correction eligibility; replacing the listed semantic fact classes with an extracted shared collection would couple the test to production dispatch structure.
# arid: disable
@pytest.mark.parametrize(
    "kind",
    [
        DecisionSubjectRevised,
        DecisionScopeEstablished,
        DecisionScopeRevised,
        DecisionDeferred,
        DecisionWorkWithdrawn,
        DecisionWorkResumed,
    ],
)
def test_every_ineligible_lifecycle_fact_kind_rejects_correction(kind):
    decision = initiate()
    if kind is DecisionWorkResumed:
        decision = defer_decision(
            decision,
            basis=human(HumanInvestmentDecisionEffect.DEFERRING),
            applicability=OPERATIVE,
            mutation=mutation(1),
        )
    meta = replace(
        decision.history[-1].metadata,
        fact_id=DecisionLifecycleFactId(uuid4()),
        sequence=DecisionLifecycleSequence(len(decision.history) + 1),
        decision_version=DecisionVersion(decision.version.value + 1),
        recorded_at=at(2),
        effective_at=at(2),
    )
    payloads = {
        DecisionSubjectRevised: DecisionSubject("A more precise same choice"),
        DecisionScopeEstablished: DecisionScope.established(PortfolioId(uuid4())),
        DecisionScopeRevised: DecisionScope.unresolved(PortfolioId(uuid4())),
        DecisionDeferred: human(HumanInvestmentDecisionEffect.DEFERRING),
        DecisionWorkWithdrawn: DecisionWorkControlBasis("stop"),
        DecisionWorkResumed: DecisionWorkControlBasis("resume"),
    }
    target = kind(meta, payloads[kind])
    decision = rebuild((*decision.history, target), observed=2)
    with pytest.raises(InvalidDecisionLifecycleCorrection, match="eligible"):
        correct(decision, target, 3, disposition=UNRESOLVED)
# arid: enable


# duplicate-code: these malformed-history cases intentionally repeat replace/rebuild syntax so each rejected identity/ancestry mutation is visible at the assertion site; a helper would hide the exact invalid shape being tested.
# arid: disable
def test_foreign_self_forward_duplicate_and_wrong_identity_targets_rejected():
    decision = initiate()
    foreign = initiate().history[0]
    with pytest.raises(InvalidDecisionLifecycleCorrection):
        correct(decision, foreign, 20, disposition=UNRESOLVED)
    initial = decision.history[0]
    decision = correct(decision, initial, 20, disposition=UNRESOLVED)
    correction = decision.history[-1]
    with pytest.raises(InvalidDecisionLifecycleCorrection):
        rebuild(
            (initial, replace(correction, target_fact_id=correction.metadata.fact_id))
        )
    with pytest.raises(InvalidDecisionHistory, match="unique"):
        rebuild(
            (
                initial,
                replace(
                    correction,
                    metadata=replace(
                        correction.metadata, fact_id=initial.metadata.fact_id
                    ),
                ),
            )
        )
    with pytest.raises(InvalidDecisionHistory, match="same Investment Decision"):
        rebuild(
            (
                initial,
                replace(
                    correction,
                    metadata=replace(
                        correction.metadata, decision_id=foreign.metadata.decision_id
                    ),
                ),
            )
        )
    # A provenance value/relationship identity cannot be mistaken for a fact ID.
    with pytest.raises(ValueError):
        replace(correction, target_fact_id=OperationId(uuid4()))
    with pytest.raises(InvalidDecisionBasis):
        replace(correction, correction_basis=ExternalResolutionBasis("wrong purpose"))
# arid: enable


@pytest.mark.parametrize(
    "attribution",
    [
        UnknownActorAttribution(),
        ContestedActorAttribution(frozenset({ActorId(uuid4()), ActorId(uuid4())})),
    ],
)
def test_correction_reconstruction_preserves_truthful_nonknown_actor(attribution):
    decision = initiate()
    decision = correct(decision, decision.history[0], 20, disposition=UNRESOLVED)
    correction = decision.history[-1]
    historical = replace(
        correction, metadata=replace(correction.metadata, actor_attribution=attribution)
    )
    assert rebuild((*decision.history[:-1], historical)).history[-1] == historical
    with pytest.raises(InvalidDecisionTransition, match="known Actor"):
        replace(mutation(30), actor_attribution=attribution)


def test_current_not_yet_effective_change_and_future_only_suppression_version():
    decision = initiate(effective=100)
    decision = correct(
        decision, decision.history[0], 20, effective=0, disposition=UNRESOLVED
    )
    assert_result(decision, UNRESOLVED, decision.history[-1])
    assert decision.version == DecisionVersion(2)
    decision = resolve(initiate(), recorded=10, effective=100)
    initial, root = decision.history
    decision = correct(decision, root, 20, effect=DISCONFIRM)
    withdrawal = decision.history[-1]
    assert_result(decision, UNRESOLVED, initial)
    assert decision.version == DecisionVersion(2)
    assert_result(query(decision, 100), UNRESOLVED, initial, withdrawal)
    assert query(decision, 100).version == DecisionVersion(2)


def test_correction_at_new_recording_boundary_compares_both_histories_there():
    decision = resolve(initiate(), recorded=10, effective=100)
    initial, root = decision.history
    # The stored view is unresolved, but the pre-command state at 120 is terminal.
    decision = correct(decision, initial, 120, effective=5, disposition=UNRESOLVED)
    assert_result(decision, SUBSTANTIVE, root)
    assert decision.version == DecisionVersion(2)


def test_long_finite_correction_chain_has_no_python_recursion_limit():
    decision = initiate()
    initial = decision.history[0]
    history = [initial]
    for sequence in range(2, 1050):
        context = mutation(0)
        meta = replace(
            initial.metadata,
            fact_id=context.fact_id,
            sequence=DecisionLifecycleSequence(sequence),
            decision_version=DecisionVersion(sequence),
            operation_id=context.operation_id,
        )
        history.append(
            DecisionLifecycleCorrected(
                meta,
                history[-1].metadata.fact_id,
                QUALIFY,
                DecisionLifecycleCorrectionBasis("independent act"),
                UNRESOLVED,
            )
        )
    decision = rebuild(history)
    assert_result(decision, UNRESOLVED, history[-1])
    assert len(decision.history) == 1049


def test_defeating_future_only_preemption_has_no_present_support():
    decision = resolve(initiate())
    root = decision.history[-1]
    decision = correct(decision, root, 20, effective=100, disposition=EXTERNAL)
    c1 = decision.history[-1]
    decision = correct(decision, c1, 30, effect=DISCONFIRM)
    c2 = decision.history[-1]
    decision = correct(decision, c2, 40, effect=DISCONFIRM)
    c3 = decision.history[-1]
    assert_result(decision, SUBSTANTIVE, root)
    assert decision.version == DecisionVersion(2)
    assert_result(query(decision, 100), EXTERNAL, c1, c3)
