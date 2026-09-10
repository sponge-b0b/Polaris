from datetime import UTC, datetime, timedelta
from uuid import uuid1, uuid4

import pytest

from polaris.domain.decisions import (
    ActorId,
    DecisionApplicability,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleCorrectionBasis,
    DecisionLifecycleCorrectionEffect,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedId,
    DecisionNotOperative,
    DecisionRelationshipAdmissionRejected,
    DecisionRelationshipBasisRole,
    DecisionRelationshipCorrectionBasis,
    DecisionRelationshipCorrectionEffect,
    DecisionRelationshipDeterminismRequired,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipFactMetadata,
    DecisionRelationshipMutationContext,
    DecisionRelationshipNotKnownAtCutoff,
    DecisionRelationshipReplayConflict,
    DecisionRelationshipState,
    DecisionRelationshipType,
    DecisionScope,
    DecisionSubject,
    DecisionVersion,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    InvalidDecisionIdentity,
    InvalidDecisionRelationshipBasis,
    InvalidDecisionRelationshipHistory,
    InvestmentDecisionId,
    KnownActorAttribution,
    OperationId,
    RenewedFromRelationshipBasis,
    SupersedesRelationshipBasis,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnknownActorAttribution,
    UnsupportedDecisionNeedBasis,
    apply_relationship_command,
    correct_decision_lifecycle,
    derive_relationship_applicability,
    initiate_decision,
    interpret_relationship,
    reconcile_relationship_replay,
    relationship_correction,
    relationship_fact,
    renew_decision,
    require_determinate_relationship_applicability,
    substantively_resolve_decision,
)

ORIGIN = datetime(2026, 9, 9, 10, tzinfo=UTC)
OPERATIVE = DecisionApplicability.OPERATIVE
SUPERSEDES = DecisionRelationshipType.SUPERSEDES
RENEWED_FROM = DecisionRelationshipType.RENEWED_FROM
QUALIFY = DecisionRelationshipCorrectionEffect.QUALIFY
DISCONFIRM = DecisionRelationshipCorrectionEffect.DISCONFIRM


def at(minutes: int) -> datetime:
    return ORIGIN + timedelta(minutes=minutes)


def lifecycle_mutation(
    recorded: int,
    effective: int | None = None,
    *,
    operation_id: OperationId | None = None,
) -> DecisionMutationContext:
    operation = operation_id or OperationId(uuid4())
    return DecisionMutationContext(
        fact_id=DecisionLifecycleFactId(uuid4()),
        operation_id=operation,
        actor_attribution=KnownActorAttribution(ActorId(uuid4())),
        trigger=TriggerProvenance(
            TriggerKind.EXTERNAL_OBSERVATION,
            f"lifecycle-{recorded}",
        ),
        technical_provenance=TechnicalProvenance(
            [TechnicalReference(TechnicalReferenceKind.REQUEST, str(uuid4()))]
        ),
        effective_at=at(recorded if effective is None else effective),
        recorded_at=at(recorded),
    )


def relationship_mutation(
    recorded: int,
    *,
    operation_id: OperationId | None = None,
    fact_id: DecisionRelationshipFactId | None = None,
) -> DecisionRelationshipMutationContext:
    return DecisionRelationshipMutationContext(
        fact_id or DecisionRelationshipFactId(uuid4()),
        operation_id or OperationId(uuid4()),
        KnownActorAttribution(ActorId(uuid4())),
        TriggerProvenance(
            TriggerKind.EXTERNAL_OBSERVATION,
            f"relationship-{recorded}",
        ),
        at(recorded),
        TechnicalProvenance(
            [TechnicalReference(TechnicalReferenceKind.REQUEST, str(uuid4()))]
        ),
    )


def initiate(
    *,
    recorded: int = 0,
    effective: int = 0,
    decision_id: InvestmentDecisionId | None = None,
    operation_id: OperationId | None = None,
):
    mutation = lifecycle_mutation(
        recorded,
        effective,
        operation_id=operation_id,
    )
    need = DecisionNeed(
        need_id=DecisionNeedId(uuid4()),
        statement="Whether to change exposure",
        effective_at=at(effective),
        recorded_at=at(recorded),
        operation_id=mutation.operation_id,
        actor_attribution=mutation.actor_attribution,
        trigger=mutation.trigger,
    )
    return initiate_decision(
        decision_id=decision_id or InvestmentDecisionId(uuid4()),
        need=need,
        subject=DecisionSubject("Whether to change exposure"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.NO_CANDIDATES,
            candidate_decision_ids=(),
            known_at=at(recorded),
        ),
        mutation=mutation,
    )


def resolve(decision, *, recorded: int, effective: int | None = None):
    return substantively_resolve_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            str(uuid4()),
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
        applicability=OPERATIVE,
        mutation=lifecycle_mutation(recorded, effective),
    )


def unsupported(decision, *, recorded: int):
    initiation = decision.history[0]
    return correct_decision_lifecycle(
        decision,
        target_fact_id=initiation.metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("unsupported Need"),
        replacement_disposition=(
            DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED
        ),
        replacement_basis=UnsupportedDecisionNeedBasis("unsupported Need"),
        mutation=lifecycle_mutation(recorded),
        applicability=OPERATIVE,
    )


def supersedes(
    source,
    target,
    *,
    effective: int,
    recorded: int,
    operation_id: OperationId | None = None,
    fact_id: DecisionRelationshipFactId | None = None,
    basis: SupersedesRelationshipBasis | None = None,
):
    mutation = relationship_mutation(
        recorded,
        operation_id=operation_id,
        fact_id=fact_id,
    )
    return relationship_fact(
        source_decision_id=source.decision_id,
        target_decision_id=target.decision_id,
        relationship_type=SUPERSEDES,
        relationship_effective_at=at(effective),
        relationship_basis=basis or SupersedesRelationshipBasis(["supersession"]),
        mutation=mutation,
    )


def apply(history, facts, decisions, *, boundary: int, new_ids=()):
    new = frozenset(new_ids)
    expected = {
        identity: decision.version
        for identity, decision in decisions.items()
        if identity not in new
    }
    return apply_relationship_command(
        history,
        facts,
        decisions=decisions,
        expected_versions=expected,
        recording_boundary=at(boundary),
        new_decision_ids=new,
    )


def query(history, source, target, effective: int, known: int | None = None):
    return interpret_relationship(
        history,
        source_decision_id=source.decision_id,
        relationship_type=SUPERSEDES,
        target_decision_id=target.decision_id,
        effective_at=at(effective),
        known_at=at(effective if known is None else known),
    )


def test_relationship_identity_is_uuid4_and_not_an_edge_key():
    identity = DecisionRelationshipFactId(uuid4())
    assert identity.value.version == 4
    with pytest.raises(InvalidDecisionIdentity):
        DecisionRelationshipFactId(uuid1())

    source = initiate()
    target = initiate()
    fact = supersedes(
        source,
        target,
        effective=0,
        recorded=0,
        fact_id=identity,
    )
    assert fact.metadata.relationship_fact_id == identity
    assert fact.source_decision_id != fact.target_decision_id


def test_relationship_and_correction_basis_roles_are_not_interchangeable():
    source = initiate()
    target = initiate()
    with pytest.raises(InvalidDecisionRelationshipBasis):
        relationship_fact(
            source_decision_id=source.decision_id,
            target_decision_id=target.decision_id,
            relationship_type=SUPERSEDES,
            relationship_effective_at=at(0),
            relationship_basis=RenewedFromRelationshipBasis(["wrong role"]),
            mutation=relationship_mutation(0),
        )

    fact = supersedes(source, target, effective=0, recorded=0)
    with pytest.raises(InvalidDecisionRelationshipBasis):
        relationship_correction(
            target_relationship_fact_id=fact.metadata.relationship_fact_id,
            effect=DISCONFIRM,
            correction_effective_at=at(10),
            correction_basis=SupersedesRelationshipBasis(["wrong correction role"]),
            mutation=relationship_mutation(10),
        )


# duplicate-code: the equivalent-support proof intentionally keeps the baseline admission inline; the later protection-requirements test owns a distinct contract and should remain independently scanned.
# arid: disable
def test_distinct_equivalent_assertions_append_and_union_support():
    source = initiate()
    target = initiate()
    first = supersedes(source, target, effective=0, recorded=0)
    one = apply(
        (),
        (first,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    source = one.decision(source.decision_id)
    target = one.decision(target.decision_id)

    second = supersedes(source, target, effective=0, recorded=10)
    two = apply(
        one.history,
        (second,),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    result = query(two.history, source, target, 10)
    assert result.state is DecisionRelationshipState.SUPPORTED
    assert result.support_fact_ids == frozenset(
        {
            first.metadata.relationship_fact_id,
            second.metadata.relationship_fact_id,
        }
    )
    assert len(result.surviving_positive_claims) == 1
    assert len(two.history) == 2
# arid: enable


def test_same_operation_replay_is_separate_from_distinct_append():
    operation = OperationId(uuid4())
    assert reconcile_relationship_replay(
        operation_id=operation,
        stored_operation_id=operation,
        semantic_request_matches=True,
    )
    with pytest.raises(DecisionRelationshipReplayConflict):
        reconcile_relationship_replay(
            operation_id=operation,
            stored_operation_id=operation,
            semantic_request_matches=False,
        )
    assert not reconcile_relationship_replay(
        operation_id=OperationId(uuid4()),
        stored_operation_id=operation,
        semantic_request_matches=True,
    )


def test_future_base_is_not_effective_and_does_not_bump_versions():
    source = initiate()
    target = initiate()
    fact = supersedes(source, target, effective=60, recorded=0)
    command = apply(
        (),
        (fact,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    result = query(command.history, source, target, 0)
    assert result.state is DecisionRelationshipState.NOT_EFFECTIVE
    assert result.support_fact_ids == frozenset()
    assert command.versioned_decision_ids == frozenset()


# duplicate-code: this is the contested sibling of the equivalent-assertion proof above; both intentionally retain the two-step append sequence so effective-time disagreement stays visible at the test site.
# arid: disable
def test_different_effective_instants_contest_without_recency_precedence():
    source = initiate()
    target = initiate()
    first = supersedes(source, target, effective=0, recorded=0)
    one = apply(
        (),
        (first,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    source = one.decision(source.decision_id)
    target = one.decision(target.decision_id)
    second = supersedes(source, target, effective=5, recorded=10)
    two = apply(
        one.history,
        (second,),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    result = query(two.history, source, target, 10)
    assert result.state is DecisionRelationshipState.CONTESTED
    assert result.support_fact_ids == frozenset(
        {
            first.metadata.relationship_fact_id,
            second.metadata.relationship_fact_id,
        }
    )
# arid: enable


def test_qualify_keeps_correction_and_replacement_instants_distinct():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=QUALIFY,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["new evidence"]),
        replacement_relationship_effective_at=at(20),
        replacement_relationship_basis=SupersedesRelationshipBasis(
            ["replacement basis"]
        ),
        mutation=relationship_mutation(30),
    )
    history = (base, correction)
    gap = query(history, source, target, 15, known=30)
    assert gap.state is DecisionRelationshipState.NOT_EFFECTIVE
    assert gap.support_fact_ids == frozenset({correction.metadata.relationship_fact_id})
    assert {item.role for item in gap.basis_contributions} == {
        DecisionRelationshipBasisRole.CORRECTION
    }

    replacement = query(history, source, target, 20, known=30)
    assert replacement.state is DecisionRelationshipState.SUPPORTED
    assert replacement.support_fact_ids == frozenset(
        {correction.metadata.relationship_fact_id}
    )
    assert {item.role for item in replacement.basis_contributions} == {
        DecisionRelationshipBasisRole.CORRECTION,
        DecisionRelationshipBasisRole.RELATIONSHIP,
    }


def test_disconfirming_future_correction_restores_without_premature_support():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    first = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(20),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(5),
    )
    second = relationship_correction(
        target_relationship_fact_id=first.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["restore"]),
        mutation=relationship_mutation(6),
    )
    early = query((base, first, second), source, target, 15)
    assert early.state is DecisionRelationshipState.SUPPORTED
    assert early.support_fact_ids == frozenset({base.metadata.relationship_fact_id})
    late = query((base, first, second), source, target, 25)
    assert late.state is DecisionRelationshipState.SUPPORTED
    assert late.support_fact_ids == frozenset(
        {
            base.metadata.relationship_fact_id,
            second.metadata.relationship_fact_id,
        }
    )


# duplicate-code: sibling positive/withdrawal branches deliberately repeat correction construction so the competing branch topology is explicit; a correction fixture would hide which branch carries each semantic claim.
# arid: disable
def test_sibling_positive_and_withdrawal_branches_are_contested():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    positive = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=QUALIFY,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["qualify"]),
        replacement_relationship_effective_at=at(0),
        replacement_relationship_basis=SupersedesRelationshipBasis(["positive"]),
        mutation=relationship_mutation(20),
    )
    withdrawal = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(20),
    )
    result = query((base, positive, withdrawal), source, target, 20)
    assert result.state is DecisionRelationshipState.CONTESTED
    assert positive.metadata.relationship_fact_id in result.support_fact_ids
    assert withdrawal.metadata.relationship_fact_id in result.support_fact_ids
# arid: enable


# duplicate-code: this withdrawn-plus-future interpretation is an independent state-partition proof; sharing its correction setup with protection/version tests would couple different contracts.
# arid: disable
def test_withdrawn_plus_future_lineage_is_not_effective_not_withdrawn():
    source = initiate()
    target = initiate()
    first = supersedes(source, target, effective=0, recorded=0)
    second = supersedes(source, target, effective=50, recorded=1)
    withdrawal = relationship_correction(
        target_relationship_fact_id=first.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(10),
    )
    result = query((first, second, withdrawal), source, target, 20)
    assert result.state is DecisionRelationshipState.NOT_EFFECTIVE
    assert withdrawal.metadata.relationship_fact_id in result.support_fact_ids
    assert second.metadata.relationship_fact_id not in result.support_fact_ids
# arid: enable


def test_missing_correction_ancestry_is_explicit_invalid_history():
    source = initiate()
    target = initiate()
    correction = relationship_correction(
        target_relationship_fact_id=DecisionRelationshipFactId(uuid4()),
        effect=DISCONFIRM,
        correction_effective_at=at(0),
        correction_basis=DecisionRelationshipCorrectionBasis(["orphan"]),
        mutation=relationship_mutation(0),
    )
    with pytest.raises(InvalidDecisionRelationshipHistory):
        query((correction,), source, target, 0)


def test_same_command_ancestry_uses_explicit_ids_not_request_order():
    source = initiate()
    target = initiate()
    operation = OperationId(uuid4())
    base_id = DecisionRelationshipFactId(uuid4())
    first_id = DecisionRelationshipFactId(uuid4())
    second_id = DecisionRelationshipFactId(uuid4())
    base = supersedes(
        source,
        target,
        effective=0,
        recorded=10,
        operation_id=operation,
        fact_id=base_id,
    )
    first = relationship_correction(
        target_relationship_fact_id=base_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(
            10,
            operation_id=operation,
            fact_id=first_id,
        ),
    )
    second = relationship_correction(
        target_relationship_fact_id=first_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["restore"]),
        mutation=relationship_mutation(
            10,
            operation_id=operation,
            fact_id=second_id,
        ),
    )
    command = apply(
        (),
        (second, first, base),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    result = query(command.history, source, target, 10)
    assert result.state is DecisionRelationshipState.SUPPORTED
    assert result.support_fact_ids == frozenset({base_id, second_id})


# duplicate-code: the correction-cycle falsifier intentionally mirrors the valid same-command ancestry setup above; extracting their shared ID/correction scaffold would hide the one edge reversal that makes the ancestry invalid.
# arid: disable
def test_same_command_correction_cycle_is_rejected():
    source = initiate()
    target = initiate()
    operation = OperationId(uuid4())
    first_id = DecisionRelationshipFactId(uuid4())
    second_id = DecisionRelationshipFactId(uuid4())
    first = relationship_correction(
        target_relationship_fact_id=second_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["one"]),
        mutation=relationship_mutation(
            10,
            operation_id=operation,
            fact_id=first_id,
        ),
    )
    second = relationship_correction(
        target_relationship_fact_id=first_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["two"]),
        mutation=relationship_mutation(
            10,
            operation_id=operation,
            fact_id=second_id,
        ),
    )
    with pytest.raises(InvalidDecisionRelationshipHistory):
        apply(
            (),
            (first, second),
            {source.decision_id: source, target.decision_id: target},
            boundary=10,
        )
# arid: enable


def test_positive_admission_rejects_unsupported_need_endpoint():
    source = initiate()
    target = unsupported(initiate(), recorded=10)
    fact = supersedes(source, target, effective=10, recorded=10)
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply(
            (),
            (fact,),
            {source.decision_id: source, target.decision_id: target},
            boundary=10,
        )


def test_renewal_creates_new_episode_and_preserves_predecessor_history():
    predecessor = resolve(initiate(), recorded=10)
    operation = OperationId(uuid4())
    new_id = InvestmentDecisionId(uuid4())
    initiation = lifecycle_mutation(20, operation_id=operation)
    need = DecisionNeed(
        need_id=DecisionNeedId(uuid4()),
        statement="Whether to revisit exposure",
        effective_at=at(20),
        recorded_at=at(20),
        operation_id=operation,
        actor_attribution=initiation.actor_attribution,
        trigger=initiation.trigger,
    )
    renewal = relationship_fact(
        source_decision_id=new_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(20),
        relationship_basis=RenewedFromRelationshipBasis(["new judgment episode"]),
        mutation=relationship_mutation(20, operation_id=operation),
    )
    prior_history = predecessor.history
    result = renew_decision(
        existing_relationship_history=(),
        renewal_facts=(renewal,),
        predecessor_decisions=(predecessor,),
        decision_id=new_id,
        need=need,
        subject=DecisionSubject("Whether to revisit exposure"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
            candidate_decision_ids=(predecessor.decision_id,),
            known_at=at(20),
            rationale="Prior judgment episode is resolved",
        ),
        initiation_mutation=initiation,
        expected_versions={predecessor.decision_id: predecessor.version},
    )
    assert result.decision.decision_id == new_id
    assert result.decision.need == need
    assert result.decision.version == DecisionVersion(1)
    updated_predecessor = result.relationship_result.decision(predecessor.decision_id)
    assert updated_predecessor.history == prior_history
    assert updated_predecessor.version == DecisionVersion(predecessor.version.value + 1)


# duplicate-code: renewal rejection keeps the complete new-episode construction beside the successful renewal above because predecessor lifecycle state is the only intended difference; a renewal fixture would hide that predicate.
# arid: disable
def test_renewal_rejects_unresolved_predecessor_at_episode_start():
    predecessor = initiate()
    operation = OperationId(uuid4())
    new_id = InvestmentDecisionId(uuid4())
    initiation = lifecycle_mutation(20, operation_id=operation)
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Whether to revisit exposure",
        at(20),
        at(20),
        operation,
        initiation.actor_attribution,
        initiation.trigger,
    )
    renewal = relationship_fact(
        source_decision_id=new_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(20),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(20, operation_id=operation),
    )
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        renew_decision(
            existing_relationship_history=(),
            renewal_facts=(renewal,),
            predecessor_decisions=(predecessor,),
            decision_id=new_id,
            need=need,
            subject=DecisionSubject("Whether to revisit exposure"),
            scope=DecisionScope.unresolved(),
            continuity=DecisionInitiationContinuity(
                determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
                candidate_decision_ids=(predecessor.decision_id,),
                known_at=at(20),
                rationale="Create a new episode",
            ),
            initiation_mutation=initiation,
            expected_versions={predecessor.decision_id: predecessor.version},
        )
# arid: enable


def test_late_omitted_renewal_can_link_existing_new_episode():
    predecessor = resolve(initiate(), recorded=10)
    source = initiate(recorded=20, effective=20)
    fact = relationship_fact(
        source_decision_id=source.decision_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(20),
        relationship_basis=RenewedFromRelationshipBasis(["omitted lineage"]),
        mutation=relationship_mutation(30),
    )
    command = apply(
        (),
        (fact,),
        {
            source.decision_id: source,
            predecessor.decision_id: predecessor,
        },
        boundary=30,
    )
    assert command.decision(source.decision_id).need == source.need
    assert command.decision(source.decision_id).history == source.history


def test_supported_and_contested_supersession_drive_applicability():
    source = initiate()
    target = initiate()
    first = supersedes(source, target, effective=0, recorded=0)
    assert (
        derive_relationship_applicability(
            target.decision_id,
            (first,),
            effective_at=at(0),
            known_at=at(0),
        )
        is DecisionApplicability.NON_OPERATIVE
    )

    second = supersedes(source, target, effective=5, recorded=10)
    assert (
        derive_relationship_applicability(
            target.decision_id,
            (first, second),
            effective_at=at(10),
            known_at=at(10),
        )
        is DecisionApplicability.CONTESTED
    )


def test_relationship_applicability_fail_closed_errors_are_typed():
    with pytest.raises(DecisionRelationshipDeterminismRequired):
        require_determinate_relationship_applicability(DecisionApplicability.CONTESTED)
    with pytest.raises(DecisionNotOperative):
        require_determinate_relationship_applicability(
            DecisionApplicability.NON_OPERATIVE
        )
    require_determinate_relationship_applicability(DecisionApplicability.OPERATIVE)


# duplicate-code: this proof intentionally repeats the resolved lifecycle command inside the relationship command to show aggregate DecisionVersion advances once; extracting the shared resolve call would hide the same-operation boundary.
# arid: disable
def test_same_command_lifecycle_and_relationship_version_only_once():
    source = initiate()
    target = initiate()
    target_baseline_version = target.version
    operation = OperationId(uuid4())
    target = substantively_resolve_decision(
        target,
        basis=TrustedHumanInvestmentDecisionBasis(
            str(uuid4()),
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
        applicability=OPERATIVE,
        mutation=lifecycle_mutation(10, operation_id=operation),
    )
    fact = supersedes(
        source,
        target,
        effective=10,
        recorded=10,
        operation_id=operation,
    )
    command = apply_relationship_command(
        (),
        (fact,),
        decisions={
            source.decision_id: source,
            target.decision_id: target,
        },
        expected_versions={
            source.decision_id: source.version,
            target.decision_id: target_baseline_version,
        },
        recording_boundary=at(10),
    )
    assert command.decision(source.decision_id).version == DecisionVersion(2)
    assert command.decision(target.decision_id).version == DecisionVersion(2)
    assert command.versioned_decision_ids == frozenset(
        {source.decision_id, target.decision_id}
    )
# arid: enable


# duplicate-code: this version/sequence proof deliberately uses the canonical one-edge admission shape; sharing its apply scaffold with future-base or protection tests would couple distinct version semantics.
# arid: disable
def test_supersession_changes_version_not_lifecycle_sequence_or_disposition():
    source = initiate()
    target = initiate()
    sequence = target.history[-1].metadata.sequence
    fact = supersedes(source, target, effective=0, recorded=0)
    command = apply(
        (),
        (fact,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    changed_target = command.decision(target.decision_id)
    assert changed_target.version == DecisionVersion(target.version.value + 1)
    assert changed_target.history[-1].metadata.sequence == sequence
    assert changed_target.disposition is DecisionLifecycleDisposition.UNRESOLVED
# arid: enable


def test_supersession_allows_one_to_many_and_many_to_one():
    a, b, c, d = initiate(), initiate(), initiate(), initiate()
    operation = OperationId(uuid4())
    facts = (
        supersedes(a, b, effective=0, recorded=0, operation_id=operation),
        supersedes(a, c, effective=0, recorded=0, operation_id=operation),
        supersedes(d, b, effective=0, recorded=0, operation_id=operation),
    )
    decisions = {item.decision_id: item for item in (a, b, c, d)}
    command = apply((), facts, decisions, boundary=0)
    assert command.versioned_decision_ids == frozenset(decisions)
    assert len(command.history) == 3


# duplicate-code: support-only versioning intentionally spells out two equivalent support facts and the baseline admission; abstracting the repeated edge construction would hide that duplicate support, not duplicate code, is the behavior under test.
# arid: disable
def test_support_only_atomic_change_versions_each_endpoint_at_most_once():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    one = apply(
        (),
        (base,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    source = one.decision(source.decision_id)
    target = one.decision(target.decision_id)
    operation = OperationId(uuid4())
    support_one = supersedes(
        source,
        target,
        effective=0,
        recorded=10,
        operation_id=operation,
    )
    support_two = supersedes(
        source,
        target,
        effective=0,
        recorded=10,
        operation_id=operation,
    )
    two = apply(
        one.history,
        (support_one, support_two),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    assert two.decision(source.decision_id).version == DecisionVersion(
        source.version.value + 1
    )
    assert two.decision(target.decision_id).version == DecisionVersion(
        target.version.value + 1
    )
# arid: enable


# duplicate-code: command admission and raw-history validation intentionally exercise the same malformed QUALIFY shape through different boundaries; keeping this command-path proof local preserves that distinction.
# arid: disable
def test_qualify_replacement_basis_must_match_root_relationship_type():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=QUALIFY,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["correction"]),
        replacement_relationship_effective_at=at(10),
        replacement_relationship_basis=RenewedFromRelationshipBasis(["wrong"]),
        mutation=relationship_mutation(10),
    )
    with pytest.raises(InvalidDecisionRelationshipBasis):
        apply(
            (base,),
            (correction,),
            {source.decision_id: source, target.decision_id: target},
            boundary=10,
        )
# arid: enable


# duplicate-code: DISCONFIRM admission deliberately mirrors correction/protection setup while changing endpoint eligibility semantics; sharing the setup would obscure the rule that DISCONFIRM bypasses later endpoint ineligibility.
# arid: disable
def test_disconfirm_bypasses_later_endpoint_lifecycle_ineligibility():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    one = apply(
        (),
        (base,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    source = one.decision(source.decision_id)
    target = unsupported(one.decision(target.decision_id), recorded=10)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw edge"]),
        mutation=relationship_mutation(10),
    )
    command = apply(
        one.history,
        (correction,),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    result = query(command.history, source, target, 10)
    assert result.state is DecisionRelationshipState.WITHDRAWN
# arid: enable


def test_command_exposes_non_cas_protection_requirements():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    one = apply(
        (),
        (base,),
        {source.decision_id: source, target.decision_id: target},
        boundary=0,
    )
    source = one.decision(source.decision_id)
    target = one.decision(target.decision_id)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(10),
    )
    two = apply(
        one.history,
        (correction,),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    requirements = two.protection_requirements
    assert requirements.endpoint_decision_ids == frozenset(
        {source.decision_id, target.decision_id}
    )
    assert base.metadata.relationship_fact_id in (
        requirements.correction_ancestry_fact_ids
    )
    assert requirements.recording_boundary == at(10)
    assert requirements.requires_complete_relationship_history
    assert requirements.requires_graph_revalidation
    assert requirements.requires_absence_revalidation


# duplicate-code: this provenance proof repeats relationship construction intentionally so it can inspect the exact emitted metadata object; extracting the setup would hide the boundary whose separation is asserted.
# arid: disable
def test_relationship_metadata_keeps_actor_trigger_and_technical_provenance_separate():
    source = initiate()
    target = initiate()
    mutation = relationship_mutation(0)
    fact = supersedes(
        source,
        target,
        effective=0,
        recorded=0,
        operation_id=mutation.operation_id,
        fact_id=mutation.fact_id,
    )
    metadata = fact.metadata
    assert metadata.actor_attribution is not metadata.trigger
    assert metadata.trigger is not metadata.technical_provenance
    assert not hasattr(source, "related_decisions")
# arid: enable


# duplicate-code: raw-history validation intentionally reconstructs the same malformed QUALIFY shape used at command admission so the test proves immutable-history validation independently of command validation.
# arid: disable
def test_raw_history_rejects_qualify_basis_for_wrong_relationship_type():
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=QUALIFY,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["correction"]),
        replacement_relationship_effective_at=at(10),
        replacement_relationship_basis=RenewedFromRelationshipBasis(["wrong"]),
        mutation=relationship_mutation(10),
    )
    with pytest.raises(InvalidDecisionRelationshipBasis):
        query((base, correction), source, target, 10)
# arid: enable


# duplicate-code: the temporal QUALIFY matrix keeps the full replacement fact visible because the replacement instant is the parameter under test; extracting a correction fixture would hide the tested boundary.
# arid: disable
@pytest.mark.parametrize("replacement_effective", [5, 10])
def test_qualify_replacement_may_precede_or_equal_correction_activation(
    replacement_effective,
):
    source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    correction = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=QUALIFY,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["correction"]),
        replacement_relationship_effective_at=at(replacement_effective),
        replacement_relationship_basis=SupersedesRelationshipBasis(["replacement"]),
        mutation=relationship_mutation(20),
    )
    result = query((base, correction), source, target, 10, known=20)
    assert result.state is DecisionRelationshipState.SUPPORTED
    assert {
        claim.relationship_effective_at for claim in result.surviving_positive_claims
    } == {at(replacement_effective)}
    assert correction.metadata.relationship_fact_id in result.support_fact_ids
# arid: enable


# duplicate-code: these renewal timing siblings intentionally repeat the complete episode/Need/relationship command so the predecessor resolution instant is the visible discriminant; a shared renewal fixture would erase that temporal proof.
# arid: disable
def test_renewal_requires_resolution_at_episode_start_not_only_claim_time():
    predecessor = resolve(initiate(), recorded=10, effective=25)
    operation = OperationId(uuid4())
    new_id = InvestmentDecisionId(uuid4())
    initiation = lifecycle_mutation(30, effective=20, operation_id=operation)
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Whether to revisit exposure",
        at(20),
        at(30),
        operation,
        initiation.actor_attribution,
        initiation.trigger,
    )
    renewal = relationship_fact(
        source_decision_id=new_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(25),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(30, operation_id=operation),
    )
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        renew_decision(
            existing_relationship_history=(),
            renewal_facts=(renewal,),
            predecessor_decisions=(predecessor,),
            decision_id=new_id,
            need=need,
            subject=DecisionSubject("Whether to revisit exposure"),
            scope=DecisionScope.unresolved(),
            continuity=DecisionInitiationContinuity(
                determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
                candidate_decision_ids=(predecessor.decision_id,),
                known_at=at(30),
                rationale="Predecessor resolves only after the new episode begins",
            ),
            initiation_mutation=initiation,
            expected_versions={predecessor.decision_id: predecessor.version},
        )


def test_renewal_allows_equal_resolution_episode_and_relationship_instants():
    predecessor = resolve(initiate(), recorded=10, effective=20)
    operation = OperationId(uuid4())
    new_id = InvestmentDecisionId(uuid4())
    initiation = lifecycle_mutation(20, effective=20, operation_id=operation)
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Whether to revisit exposure",
        at(20),
        at(20),
        operation,
        initiation.actor_attribution,
        initiation.trigger,
    )
    renewal = relationship_fact(
        source_decision_id=new_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(20),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(20, operation_id=operation),
    )
    result = renew_decision(
        existing_relationship_history=(),
        renewal_facts=(renewal,),
        predecessor_decisions=(predecessor,),
        decision_id=new_id,
        need=need,
        subject=DecisionSubject("Whether to revisit exposure"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
            candidate_decision_ids=(predecessor.decision_id,),
            known_at=at(20),
            rationale="Resolution is an established prerequisite at the shared instant",
        ),
        initiation_mutation=initiation,
        expected_versions={predecessor.decision_id: predecessor.version},
    )
    assert result.decision.version == DecisionVersion(1)
# arid: enable


def test_resolved_supersession_target_preserves_lifecycle_history():
    source = initiate()
    target = resolve(initiate(), recorded=10)
    target_history = target.history
    fact = supersedes(source, target, effective=10, recorded=20)
    result = apply(
        (),
        (fact,),
        {source.decision_id: source, target.decision_id: target},
        boundary=20,
    )
    updated_target = result.decision(target.decision_id)
    assert updated_target.history == target_history
    assert (
        query(result.history, source, target, 20).state
        is DecisionRelationshipState.SUPPORTED
    )


# duplicate-code: withdrawn/future applicability intentionally repeats a correction-plus-supersession history so the lack of operative effect is explicit; sharing it with protection/contest fixtures would couple different applicability claims.
# arid: disable
def test_withdrawn_and_not_effective_supersession_do_not_reduce_applicability():
    source = initiate()
    future_source = initiate()
    target = initiate()
    base = supersedes(source, target, effective=0, recorded=0)
    withdrawal = relationship_correction(
        target_relationship_fact_id=base.metadata.relationship_fact_id,
        effect=DISCONFIRM,
        correction_effective_at=at(10),
        correction_basis=DecisionRelationshipCorrectionBasis(["withdraw"]),
        mutation=relationship_mutation(10),
    )
    future = supersedes(future_source, target, effective=20, recorded=10)
    applicability = derive_relationship_applicability(
        target.decision_id,
        (base, withdrawal, future),
        effective_at=at(10),
        known_at=at(10),
    )
    assert applicability is DecisionApplicability.OPERATIVE
# arid: enable


def test_contested_incoming_supersession_wins_over_other_clean_support():
    contested_source = initiate()
    clean_source = initiate()
    target = initiate()
    first = supersedes(contested_source, target, effective=0, recorded=0)
    second = supersedes(contested_source, target, effective=5, recorded=10)
    clean = supersedes(clean_source, target, effective=0, recorded=10)
    applicability = derive_relationship_applicability(
        target.decision_id,
        (first, second, clean),
        effective_at=at(10),
        known_at=at(10),
    )
    assert applicability is DecisionApplicability.CONTESTED


def test_positive_admission_rejects_missing_not_effective_and_contested_endpoints():
    source = initiate()
    target = initiate()
    missing = supersedes(source, target, effective=0, recorded=10)
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply((), (missing,), {source.decision_id: source}, boundary=10)

    future_source = initiate(recorded=0, effective=20)
    not_effective = supersedes(future_source, target, effective=10, recorded=20)
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply(
            (),
            (not_effective,),
            {future_source.decision_id: future_source, target.decision_id: target},
            boundary=20,
        )

    contested_target = resolve(initiate(), recorded=5)
    root = contested_target.history[-1]
    contested_target = correct_decision_lifecycle(
        contested_target,
        target_fact_id=root.metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("external correction"),
        replacement_disposition=DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
        replacement_basis=ExternalResolutionBasis("external correction"),
        mutation=lifecycle_mutation(10),
        applicability=OPERATIVE,
    )
    contested_target = correct_decision_lifecycle(
        contested_target,
        target_fact_id=root.metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.DISCONFIRM,
        correction_basis=DecisionLifecycleCorrectionBasis("withdraw resolution"),
        replacement_disposition=None,
        replacement_basis=None,
        mutation=lifecycle_mutation(15),
        applicability=OPERATIVE,
    )
    contested = supersedes(source, contested_target, effective=15, recorded=20)
    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply(
            (),
            (contested,),
            {
                source.decision_id: source,
                contested_target.decision_id: contested_target,
            },
            boundary=20,
        )


def test_relationship_fact_identity_is_type_distinct_from_other_uuid_identities():
    shared = uuid4()
    relationship_id = DecisionRelationshipFactId(shared)
    assert relationship_id != InvestmentDecisionId(shared)
    assert relationship_id != DecisionLifecycleFactId(shared)
    assert relationship_id != OperationId(shared)
    assert relationship_id != ActorId(shared)


def test_no_known_relationship_base_is_not_found_not_not_effective():
    source = initiate()
    target = initiate()
    with pytest.raises(DecisionRelationshipNotKnownAtCutoff):
        query((), source, target, 0)


# duplicate-code: this later-knowledge renewal rejection intentionally repeats the complete renewal episode so the predecessor's state at episode start versus relationship time remains explicit; a shared fixture would hide that two-time predicate.
# arid: disable
def test_renewal_rejects_resolved_start_but_unresolved_relationship_instant():
    predecessor = resolve(initiate(), recorded=5, effective=5)
    resolution = predecessor.history[-1]
    predecessor = correct_decision_lifecycle(
        predecessor,
        target_fact_id=resolution.metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("later lifecycle knowledge"),
        replacement_disposition=DecisionLifecycleDisposition.UNRESOLVED,
        replacement_basis=None,
        mutation=lifecycle_mutation(30, effective=25),
        applicability=OPERATIVE,
    )

    assert (
        predecessor.effective_at(
            at(20), known_at=at(30), applicability=OPERATIVE
        ).disposition
        is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    )
    assert (
        predecessor.effective_at(
            at(30), known_at=at(30), applicability=OPERATIVE
        ).disposition
        is DecisionLifecycleDisposition.UNRESOLVED
    )

    operation = OperationId(uuid4())
    new_id = InvestmentDecisionId(uuid4())
    initiation = lifecycle_mutation(40, effective=20, operation_id=operation)
    need = DecisionNeed(
        DecisionNeedId(uuid4()),
        "Whether to revisit exposure",
        at(20),
        at(40),
        operation,
        initiation.actor_attribution,
        initiation.trigger,
    )
    renewal = relationship_fact(
        source_decision_id=new_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(30),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(40, operation_id=operation),
    )

    with pytest.raises(DecisionRelationshipAdmissionRejected):
        renew_decision(
            existing_relationship_history=(),
            renewal_facts=(renewal,),
            predecessor_decisions=(predecessor,),
            decision_id=new_id,
            need=need,
            subject=DecisionSubject("Whether to revisit exposure"),
            scope=DecisionScope.unresolved(),
            continuity=DecisionInitiationContinuity(
                determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
                candidate_decision_ids=(predecessor.decision_id,),
                known_at=at(40),
                rationale="Predecessor no longer resolved at relationship time",
            ),
            initiation_mutation=initiation,
            expected_versions={predecessor.decision_id: predecessor.version},
        )
# arid: enable


def test_later_endpoint_correction_preserves_relationship_and_aggregate_version():
    source = initiate()
    target = resolve(initiate(), recorded=5, effective=5)
    fact = supersedes(source, target, effective=5, recorded=10)

    command = apply(
        (),
        (fact,),
        {source.decision_id: source, target.decision_id: target},
        boundary=10,
    )
    source = command.decision(source.decision_id)
    target = command.decision(target.decision_id)
    before = query(command.history, source, target, 10)

    version_after_relationship = target.version
    resolution = target.history[-1]

    target = correct_decision_lifecycle(
        target,
        target_fact_id=resolution.metadata.fact_id,
        effect=DecisionLifecycleCorrectionEffect.QUALIFY,
        correction_basis=DecisionLifecycleCorrectionBasis("later lifecycle correction"),
        replacement_disposition=DecisionLifecycleDisposition.UNRESOLVED,
        replacement_basis=None,
        mutation=lifecycle_mutation(20, effective=15),
        applicability=OPERATIVE,
    )

    assert target.disposition is DecisionLifecycleDisposition.UNRESOLVED
    assert target.version == DecisionVersion(version_after_relationship.value + 1)
    assert target.history[-1].metadata.decision_version == target.version

    after = query(command.history, source, target, 20)
    assert after.state is DecisionRelationshipState.SUPPORTED
    assert after.support_fact_ids == before.support_fact_ids


def test_endpoint_history_mapping_must_match_relationship_identity():
    source = initiate()
    target = initiate()
    imposter = initiate()
    fact = supersedes(source, target, effective=0, recorded=0)

    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply_relationship_command(
            (),
            (fact,),
            decisions={
                source.decision_id: imposter,
                target.decision_id: target,
            },
            expected_versions={
                source.decision_id: imposter.version,
                target.decision_id: target.version,
            },
            recording_boundary=at(0),
        )


def test_existing_version_one_decision_cannot_be_declared_same_command_new():
    source = initiate(recorded=0)
    target = initiate(recorded=0)
    fact = supersedes(source, target, effective=10, recorded=10)

    with pytest.raises(InvalidDecisionRelationshipHistory):
        apply_relationship_command(
            (),
            (fact,),
            decisions={
                source.decision_id: source,
                target.decision_id: target,
            },
            expected_versions={target.decision_id: target.version},
            recording_boundary=at(10),
            new_decision_ids={source.decision_id},
        )


def test_live_command_requires_known_actor_but_raw_history_preserves_unknown():
    source = initiate()
    target = initiate()
    valid = supersedes(source, target, effective=0, recorded=0)

    raw = DecisionRelationshipFact(
        DecisionRelationshipFactMetadata(
            valid.metadata.relationship_fact_id,
            valid.metadata.operation_id,
            UnknownActorAttribution(),
            valid.metadata.trigger,
            valid.metadata.technical_provenance,
            valid.metadata.recorded_at,
        ),
        valid.source_decision_id,
        valid.target_decision_id,
        valid.relationship_type,
        valid.relationship_effective_at,
        valid.relationship_basis,
    )

    assert query((raw,), source, target, 0).state is DecisionRelationshipState.SUPPORTED

    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply(
            (),
            (raw,),
            {
                source.decision_id: source,
                target.decision_id: target,
            },
            boundary=0,
        )


# duplicate-code: own-Need renewal is a semantic admission falsifier, so the explicit Decision/relationship construction remains local instead of being routed through the successful renewal helper path it is intended to challenge.
# arid: disable
def test_renewed_from_requires_source_own_new_decision_need():
    predecessor = resolve(initiate(), recorded=5, effective=0)

    source = initiate_decision(
        decision_id=InvestmentDecisionId(uuid4()),
        need=predecessor.need,
        subject=DecisionSubject("Whether to revisit exposure"),
        scope=DecisionScope.unresolved(),
        continuity=DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
            candidate_decision_ids=(predecessor.decision_id,),
            known_at=at(10),
            rationale="Attempted renewal reuses the predecessor Need",
        ),
        mutation=lifecycle_mutation(10, effective=0),
    )

    fact = relationship_fact(
        source_decision_id=source.decision_id,
        target_decision_id=predecessor.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(10),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(10),
    )

    with pytest.raises(DecisionRelationshipAdmissionRejected):
        apply(
            (),
            (fact,),
            {
                source.decision_id: source,
                predecessor.decision_id: predecessor,
            },
            boundary=10,
        )
# arid: enable


def test_applicability_validates_identity_and_time_before_empty_fast_path():
    decision = initiate()

    with pytest.raises(InvalidDecisionIdentity):
        derive_relationship_applicability(
            "not-a-decision-id",
            (),
            effective_at=at(0),
            known_at=at(0),
        )

    naive = datetime(2026, 9, 9, 10)

    with pytest.raises(ValueError):
        derive_relationship_applicability(
            decision.decision_id,
            (),
            effective_at=naive,
            known_at=at(0),
        )

    with pytest.raises(ValueError):
        derive_relationship_applicability(
            decision.decision_id,
            (),
            effective_at=at(0),
            known_at=naive,
        )

    assert (
        derive_relationship_applicability(
            decision.decision_id,
            (),
            effective_at=at(0),
            known_at=at(0),
        )
        is DecisionApplicability.OPERATIVE
    )
