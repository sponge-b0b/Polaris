from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import pytest

from polaris.domain.decisions import (
    ActorId,
    ContestedActorAttribution,
    DecisionApplicability,
    DecisionApplicabilityContested,
    DecisionContinuity,
    DecisionDeferred,
    DecisionExternallyResolved,
    DecisionInitiated,
    DecisionInitiationContinuity,
    DecisionInitiationDetermination,
    DecisionLifecycleDisposition,
    DecisionLifecycleFactId,
    DecisionLifecycleFactMetadata,
    DecisionLifecycleSequence,
    DecisionMutationContext,
    DecisionNeed,
    DecisionNeedAlreadyGrounded,
    DecisionNeedId,
    DecisionNotOperative,
    DecisionScope,
    DecisionScopeEstablished,
    DecisionScopeRevised,
    DecisionSubject,
    DecisionSubjectRevised,
    DecisionSubstantivelyResolved,
    DecisionVersion,
    DecisionWorkControlBasis,
    DecisionWorkPosture,
    DecisionWorkResumed,
    DecisionWorkWithdrawn,
    ExternalResolutionBasis,
    HumanInvestmentDecisionEffect,
    IndependentChoiceRequiresNewDecision,
    InvalidDecisionBasis,
    InvalidDecisionHistory,
    InvalidDecisionIdentity,
    InvalidDecisionScope,
    InvalidDecisionTransition,
    InvestmentDecision,
    InvestmentDecisionId,
    KnownActorAttribution,
    OperationId,
    PortfolioId,
    TechnicalProvenance,
    TechnicalReference,
    TechnicalReferenceKind,
    TriggerKind,
    TriggerProvenance,
    TrustedHumanInvestmentDecisionBasis,
    UnknownActorAttribution,
    defer_decision,
    establish_or_revise_scope,
    externally_resolve_decision,
    find_reconciliation_requirements,
    initiate_decision,
    reconstruct_decision,
    resume_decision_work,
    revise_subject,
    substantively_resolve_decision,
    withdraw_decision_work,
)

NOW = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def portfolio_id() -> PortfolioId:
    return PortfolioId(uuid4())


def decision_id() -> InvestmentDecisionId:
    return InvestmentDecisionId(uuid4())


def need_id() -> DecisionNeedId:
    return DecisionNeedId(uuid4())


def fact_id() -> DecisionLifecycleFactId:
    return DecisionLifecycleFactId(uuid4())


def operation_id() -> OperationId:
    return OperationId(uuid4())


def actor() -> KnownActorAttribution:
    return KnownActorAttribution(ActorId(uuid4()))


def trigger() -> TriggerProvenance:
    return TriggerProvenance(TriggerKind.HUMAN_REQUEST, "request-1")


def technical() -> TechnicalProvenance:
    return TechnicalProvenance(
        [TechnicalReference(TechnicalReferenceKind.REQUEST, "request-1")]
    )


def need(*, attribution=None) -> DecisionNeed:
    return DecisionNeed(
        need_id=need_id(),
        statement="A material allocation choice now requires deliberate judgment.",
        effective_at=NOW,
        recorded_at=NOW,
        operation_id=operation_id(),
        actor_attribution=attribution if attribution is not None else actor(),
        trigger=trigger(),
        technical_provenance=technical(),
    )


def continuity(*, candidates=(), rationale=None) -> DecisionInitiationContinuity:
    determination = (
        DecisionInitiationDetermination.NO_CANDIDATES
        if not candidates
        else DecisionInitiationDetermination.EXPLICIT_CREATE_NEW
    )
    return DecisionInitiationContinuity(
        determination=determination,
        candidate_decision_ids=candidates,
        known_at=NOW,
        rationale=rationale,
    )


def mutation() -> DecisionMutationContext:
    return DecisionMutationContext(
        fact_id=fact_id(),
        operation_id=operation_id(),
        actor_attribution=actor(),
        trigger=trigger(),
        technical_provenance=technical(),
        effective_at=NOW,
        recorded_at=NOW,
    )


def create_decision(*, decision_need=None, scope=None) -> InvestmentDecision:
    return initiate_decision(
        decision_id=decision_id(),
        need=decision_need or need(),
        subject=DecisionSubject("Whether to increase the portfolio's SPY exposure."),
        scope=scope or DecisionScope.unresolved(),
        continuity=continuity(),
        mutation=mutation(),
    )


# duplicate-code: this raw metadata builder intentionally mirrors other
# provenance-bearing fixtures so malformed-history tests can construct exact lifecycle
# facts locally; sharing it with mutation/Need builders would couple different fixture
# semantics.
# arid: disable
def metadata(*, identity, sequence, version, attribution=None):
    return DecisionLifecycleFactMetadata(
        fact_id=fact_id(),
        decision_id=identity,
        sequence=DecisionLifecycleSequence(sequence),
        decision_version=DecisionVersion(version),
        operation_id=operation_id(),
        actor_attribution=attribution if attribution is not None else actor(),
        trigger=trigger(),
        technical_provenance=technical(),
        effective_at=NOW,
        recorded_at=NOW,
    )


# arid: enable


def human_basis(
    effect: HumanInvestmentDecisionEffect,
) -> TrustedHumanInvestmentDecisionBasis:
    return TrustedHumanInvestmentDecisionBasis("human-investment-decision-1", effect)


def work_basis() -> DecisionWorkControlBasis:
    return DecisionWorkControlBasis("work-control-1")


def external_basis() -> ExternalResolutionBasis:
    return ExternalResolutionBasis("market-closed-choice-1")


def test_uuid_identities_are_distinct_and_reject_invalid_values() -> None:
    value = uuid4()
    ids = (
        PortfolioId(value),
        ActorId(value),
        InvestmentDecisionId(value),
        DecisionNeedId(value),
        DecisionLifecycleFactId(value),
        OperationId(value),
    )
    assert len({type(item) for item in ids}) == 6
    assert InvestmentDecisionId(value) != DecisionNeedId(value)
    with pytest.raises((TypeError, InvalidDecisionIdentity)):
        InvestmentDecisionId("not-a-uuid")
    with pytest.raises(ValueError):
        PortfolioId(UUID("00000000-0000-1000-8000-000000000000"))


def test_actor_attribution_has_no_authority_or_actor_kind() -> None:
    known = actor()
    contested = ContestedActorAttribution(frozenset({known.actor_id, ActorId(uuid4())}))
    assert known.actor_id in contested.candidate_actor_ids
    assert UnknownActorAttribution() != known
    assert not hasattr(known, "authorized")
    assert not hasattr(known, "kind")


def test_live_mutation_requires_known_actor_but_reconstruction_allows_unknown() -> None:
    unknown_need = need(attribution=UnknownActorAttribution())
    with pytest.raises(InvalidDecisionTransition, match="known Actor Attribution"):
        initiate_decision(
            decision_id=decision_id(),
            need=unknown_need,
            subject=DecisionSubject("Whether to change exposure."),
            scope=DecisionScope.unresolved(),
            continuity=continuity(),
            mutation=mutation(),
        )
    identity = decision_id()
    fact = DecisionInitiated(
        metadata(
            identity=identity,
            sequence=1,
            version=1,
            attribution=UnknownActorAttribution(),
        ),
        unknown_need,
        DecisionSubject("Whether to change exposure."),
        DecisionScope.unresolved(),
        continuity(),
    )
    assert (
        reconstruct_decision(
            [fact], observed_at=NOW, applicability=DecisionApplicability.OPERATIVE
        ).decision_id
        == identity
    )


def test_need_subject_time_and_scope_contracts() -> None:
    future = NOW + timedelta(days=1)
    decision_need = DecisionNeed(
        need_id=need_id(),
        statement="A choice warrants deliberate judgment.",
        effective_at=future,
        recorded_at=NOW,
        operation_id=operation_id(),
        actor_attribution=actor(),
        trigger=trigger(),
    )
    assert decision_need.effective_at > decision_need.recorded_at
    assert DecisionSubject("  Whether to add duration risk.  ").statement == (
        "Whether to add duration risk."
    )
    first, second = portfolio_id(), portfolio_id()
    assert DecisionScope.unresolved(first, second) == DecisionScope.unresolved(
        second, first
    )
    with pytest.raises(InvalidDecisionScope, match="duplicate"):
        DecisionScope.unresolved(first, first)
    with pytest.raises(InvalidDecisionScope, match="at least one"):
        DecisionScope.established()


def test_provenance_is_constrained_unordered_and_duplicate_free() -> None:
    first = TechnicalReference(TechnicalReferenceKind.MODEL_INVOCATION, "model-7")
    second = TechnicalReference(TechnicalReferenceKind.TRACE, "trace-2")
    assert TechnicalProvenance([first, second]) == TechnicalProvenance([second, first])
    with pytest.raises(ValueError, match="duplicate"):
        TechnicalProvenance([first, first])
    with pytest.raises(TypeError):
        TriggerProvenance("arbitrary", "x")


def test_initiation_continuity_requires_rationale_for_candidate_override() -> None:
    candidate = decision_id()
    with pytest.raises(InvalidDecisionHistory, match="requires a rationale"):
        DecisionInitiationContinuity(
            determination=DecisionInitiationDetermination.EXPLICIT_CREATE_NEW,
            candidate_decision_ids=[candidate],
            known_at=NOW,
        )
    value = continuity(
        candidates=(candidate,), rationale="Independent investment matter."
    )
    assert value.candidate_decision_ids == frozenset({candidate})


def test_initiation_version_sequence_created_at_and_need_reuse() -> None:
    decision = create_decision()
    initiation = decision.history[0]
    assert initiation.metadata.sequence == DecisionLifecycleSequence(1)
    assert decision.version == DecisionVersion(1)
    assert decision.created_at == NOW
    assert decision.disposition is DecisionLifecycleDisposition.UNRESOLVED
    assert decision.work_posture is DecisionWorkPosture.ACTIVE
    existing = decision_id()
    with pytest.raises(DecisionNeedAlreadyGrounded):
        initiate_decision(
            decision_id=decision_id(),
            need=need(),
            subject=DecisionSubject("Whether to resize SPY."),
            scope=DecisionScope.unresolved(),
            continuity=continuity(),
            mutation=mutation(),
            existing_decision_for_need=existing,
        )


def test_subject_revision_noop_change_and_independent_choice() -> None:
    decision = create_decision()
    assert (
        revise_subject(
            decision,
            subject=decision.subject,
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
        == decision
    )
    revised = revise_subject(
        decision,
        subject=DecisionSubject("Whether to modestly increase SPY exposure."),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert isinstance(revised.history[-1], DecisionSubjectRevised)
    assert revised.version == DecisionVersion(2)
    with pytest.raises(IndependentChoiceRequiresNewDecision):
        revise_subject(
            decision,
            subject=DecisionSubject("Whether to hedge unrelated FX exposure."),
            continuity=DecisionContinuity.INDEPENDENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )


# duplicate-code: Subject and Scope continuity are separate public behaviors; this test
# keeps the full Scope command signatures visible rather than sharing an invocation
# scaffold with the Subject proof above.
# arid: disable
def test_scope_transition_fact_meanings_and_noop() -> None:
    first, second = portfolio_id(), portfolio_id()
    decision = create_decision(scope=DecisionScope.unresolved(first))
    revised = establish_or_revise_scope(
        decision,
        scope=DecisionScope.unresolved(first, second),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert isinstance(revised.history[-1], DecisionScopeRevised)
    established = establish_or_revise_scope(
        revised,
        scope=DecisionScope.established(first, second),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert isinstance(established.history[-1], DecisionScopeEstablished)
    assert (
        establish_or_revise_scope(
            established,
            scope=established.scope,
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
        == established
    )
    with pytest.raises(InvalidDecisionTransition, match="cannot become unresolved"):
        establish_or_revise_scope(
            established,
            scope=DecisionScope.unresolved(first, second),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )


# arid: enable


def test_sequence_and_decision_version_are_distinct_and_version_may_gap() -> None:
    assert DecisionLifecycleSequence(2) != DecisionVersion(2)
    identity = decision_id()
    first = DecisionInitiated(
        metadata(identity=identity, sequence=1, version=1),
        need(),
        DecisionSubject("Whether to change SPY exposure."),
        DecisionScope.unresolved(),
        continuity(),
    )
    second = DecisionSubjectRevised(
        metadata(identity=identity, sequence=2, version=4),
        DecisionSubject("Whether to modestly change SPY exposure."),
    )
    rebuilt = reconstruct_decision(
        [first, second], observed_at=NOW, applicability=DecisionApplicability.OPERATIVE
    )
    assert rebuilt.version == DecisionVersion(4)
    assert rebuilt.history[-1].metadata.sequence == DecisionLifecycleSequence(2)


def test_reconstruction_rejects_invalid_identity_fact_and_sequence_history() -> None:
    identity = decision_id()
    first_meta = metadata(identity=identity, sequence=1, version=1)
    with pytest.raises(InvalidDecisionHistory, match="start with"):
        reconstruct_decision(
            [DecisionSubjectRevised(first_meta, DecisionSubject("changed"))],
            observed_at=NOW,
            applicability=DecisionApplicability.OPERATIVE,
        )
    initiation = DecisionInitiated(
        first_meta,
        need(),
        DecisionSubject("Whether to change exposure."),
        DecisionScope.unresolved(),
        continuity(),
    )
    mixed = DecisionSubjectRevised(
        metadata(identity=decision_id(), sequence=2, version=2),
        DecisionSubject("changed"),
    )
    with pytest.raises(InvalidDecisionHistory, match="same Investment Decision"):
        reconstruct_decision(
            [initiation, mixed],
            observed_at=NOW,
            applicability=DecisionApplicability.OPERATIVE,
        )
    gap = DecisionSubjectRevised(
        metadata(identity=identity, sequence=3, version=2),
        DecisionSubject("changed"),
    )
    with pytest.raises(InvalidDecisionHistory, match="contiguous"):
        reconstruct_decision(
            [initiation, gap],
            observed_at=NOW,
            applicability=DecisionApplicability.OPERATIVE,
        )


def test_public_aggregate_construction_is_closed_and_values_are_immutable() -> None:
    with pytest.raises(TypeError):
        InvestmentDecision()
    decision = create_decision()
    with pytest.raises((AttributeError, FrozenInstanceError)):
        decision._version = DecisionVersion(99)
    with pytest.raises(FrozenInstanceError):
        decision.subject.statement = "mutated"


def test_duplicate_need_groundings_are_preserved_for_reconciliation() -> None:
    shared = need()
    first, second = (
        create_decision(decision_need=shared),
        create_decision(decision_need=shared),
    )
    requirements = find_reconciliation_requirements([first, second])
    assert len(requirements) == 1
    assert requirements[0].need_id == shared.need_id
    assert requirements[0].decision_ids == frozenset(
        {first.decision_id, second.decision_id}
    )


def test_superseded_public_foundation_names_are_not_exported() -> None:
    import polaris.domain.decisions as decisions

    for removed in (
        "ActorKind",
        "BusinessBasis",
        "BusinessReference",
        "FactMetadata",
        "PortfolioRef",
        "DecisionSubjectRefined",
        "DecisionScopeRefined",
        "refine_subject",
        "refine_scope",
    ):
        assert not hasattr(decisions, removed)


def test_lifecycle_work_posture_and_applicability_are_distinct_typed_concepts() -> None:
    assert DecisionLifecycleDisposition.UNRESOLVED != DecisionWorkPosture.ACTIVE
    assert DecisionApplicability.OPERATIVE != DecisionWorkPosture.ACTIVE
    assert set(DecisionLifecycleDisposition) == {
        DecisionLifecycleDisposition.UNRESOLVED,
        DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED,
        DecisionLifecycleDisposition.EXTERNALLY_RESOLVED,
        DecisionLifecycleDisposition.NEED_RETRACTED_UNSUPPORTED,
    }
    assert set(DecisionWorkPosture) == {
        DecisionWorkPosture.ACTIVE,
        DecisionWorkPosture.DEFERRED,
        DecisionWorkPosture.WITHDRAWN,
    }


def test_deferral_and_redeferral_require_trusted_deferring_basis() -> None:
    decision = create_decision()
    deferred = defer_decision(
        decision,
        basis=human_basis(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert deferred.decision_id == decision.decision_id
    assert deferred.work_posture is DecisionWorkPosture.DEFERRED
    assert isinstance(deferred.history[-1], DecisionDeferred)
    assert deferred.history[-1].metadata.sequence == DecisionLifecycleSequence(2)
    assert deferred.version == DecisionVersion(2)

    redeferred = defer_decision(
        deferred,
        basis=TrustedHumanInvestmentDecisionBasis(
            "human-investment-decision-2",
            HumanInvestmentDecisionEffect.DEFERRING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert redeferred.decision_id == decision.decision_id
    assert redeferred.work_posture is DecisionWorkPosture.DEFERRED
    assert isinstance(redeferred.history[-1], DecisionDeferred)
    assert redeferred.history[-1].metadata.sequence == DecisionLifecycleSequence(3)
    assert redeferred.version == DecisionVersion(3)
    assert len(redeferred.history) == len(deferred.history) + 1

    with pytest.raises(InvalidDecisionBasis):
        defer_decision(
            decision,
            basis=human_basis(HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING),
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )


def test_advisory_and_unauthorized_references_cannot_satisfy_trusted_basis() -> None:
    decision = create_decision()
    for invalid in (
        "analytical-advisory-human-judgment",
        "unauthorized-attempted-authority-act",
    ):
        with pytest.raises(InvalidDecisionBasis):
            defer_decision(
                decision,
                basis=cast(TrustedHumanInvestmentDecisionBasis, invalid),
                applicability=DecisionApplicability.OPERATIVE,
                mutation=mutation(),
            )


def test_work_withdrawal_and_resumption_preserve_identity_and_same_choice() -> None:
    decision = create_decision()
    withdrawn = withdraw_decision_work(
        decision,
        basis=work_basis(),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert withdrawn.decision_id == decision.decision_id
    assert withdrawn.work_posture is DecisionWorkPosture.WITHDRAWN
    assert isinstance(withdrawn.history[-1], DecisionWorkWithdrawn)

    resumed = resume_decision_work(
        withdrawn,
        basis=work_basis(),
        continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert resumed.decision_id == decision.decision_id
    assert resumed.work_posture is DecisionWorkPosture.ACTIVE
    assert isinstance(resumed.history[-1], DecisionWorkResumed)

    with pytest.raises(IndependentChoiceRequiresNewDecision):
        resume_decision_work(
            withdrawn,
            basis=work_basis(),
            continuity=DecisionContinuity.INDEPENDENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )


def test_ordinary_work_fails_closed_for_nonoperative_or_contested_applicability() -> (
    None
):
    decision = create_decision()
    with pytest.raises(DecisionNotOperative):
        defer_decision(
            decision,
            basis=human_basis(HumanInvestmentDecisionEffect.DEFERRING),
            applicability=DecisionApplicability.NON_OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(DecisionApplicabilityContested):
        withdraw_decision_work(
            decision,
            basis=work_basis(),
            applicability=DecisionApplicability.CONTESTED,
            mutation=mutation(),
        )
    with pytest.raises(DecisionNotOperative):
        revise_subject(
            decision,
            subject=DecisionSubject("Whether to reduce SPY exposure."),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.NON_OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(DecisionApplicabilityContested):
        establish_or_revise_scope(
            decision,
            scope=DecisionScope.unresolved(portfolio_id()),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.CONTESTED,
            mutation=mutation(),
        )


def test_substantive_resolution_requires_explicit_resolving_effect() -> None:
    decision = create_decision()
    with pytest.raises(InvalidDecisionBasis):
        substantively_resolve_decision(
            decision,
            basis=TrustedHumanInvestmentDecisionBasis(
                "recommendation-rejection-requesting-more-judgment",
                HumanInvestmentDecisionEffect.DEFERRING,
            ),
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    assert decision.disposition is DecisionLifecycleDisposition.UNRESOLVED
    assert len(decision.history) == 1

    resolved = substantively_resolve_decision(
        decision,
        basis=TrustedHumanInvestmentDecisionBasis(
            "human-investment-decision-hold-no-action",
            HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING,
        ),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )
    assert resolved.disposition is DecisionLifecycleDisposition.SUBSTANTIVELY_RESOLVED
    assert resolved.work_posture is None
    assert isinstance(resolved.history[-1], DecisionSubstantivelyResolved)


def test_external_resolution_is_distinct_from_human_resolution() -> None:
    decision = create_decision()
    resolved = externally_resolve_decision(
        decision,
        basis=external_basis(),
        mutation=mutation(),
    )
    assert resolved.disposition is DecisionLifecycleDisposition.EXTERNALLY_RESOLVED
    assert resolved.work_posture is None
    fact = resolved.history[-1]
    assert isinstance(fact, DecisionExternallyResolved)
    assert isinstance(fact.basis, ExternalResolutionBasis)
    assert not isinstance(fact.basis, TrustedHumanInvestmentDecisionBasis)


# duplicate-code: this fail-closed matrix intentionally invokes every public
# ordinary-work command explicitly so the command-specific arguments and terminal-state
# behavior remain independently visible; a callable table/helper would hide the API
# contract being proved.
# arid: disable
def test_resolved_decisions_reject_ordinary_work_and_changed_subject_scope() -> None:
    decision = create_decision()
    resolved = substantively_resolve_decision(
        decision,
        basis=human_basis(HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=mutation(),
    )

    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        defer_decision(
            resolved,
            basis=human_basis(HumanInvestmentDecisionEffect.DEFERRING),
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        withdraw_decision_work(
            resolved,
            basis=work_basis(),
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        substantively_resolve_decision(
            resolved,
            basis=human_basis(HumanInvestmentDecisionEffect.SUBSTANTIVELY_RESOLVING),
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        resume_decision_work(
            resolved,
            basis=work_basis(),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        externally_resolve_decision(
            resolved,
            basis=external_basis(),
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        revise_subject(
            resolved,
            subject=DecisionSubject("Whether to change a resolved choice."),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )
    with pytest.raises(InvalidDecisionTransition, match="resolved Decision"):
        establish_or_revise_scope(
            resolved,
            scope=DecisionScope.established(portfolio_id()),
            continuity=DecisionContinuity.SAME_COHERENT_CHOICE,
            applicability=DecisionApplicability.OPERATIVE,
            mutation=mutation(),
        )


# arid: enable


# duplicate-code: this attribution/provenance proof repeats an ordinary command call
# intentionally so it can assert the exact metadata emitted by that boundary; extracting
# the setup would hide the object whose provenance is under test.
# arid: disable
def test_new_lifecycle_facts_preserve_separate_attribution_and_provenance() -> None:
    decision = create_decision()
    context = mutation()
    deferred = defer_decision(
        decision,
        basis=human_basis(HumanInvestmentDecisionEffect.DEFERRING),
        applicability=DecisionApplicability.OPERATIVE,
        mutation=context,
    )
    metadata = deferred.history[-1].metadata
    assert metadata.actor_attribution == context.actor_attribution
    assert metadata.trigger == context.trigger
    assert metadata.technical_provenance == context.technical_provenance
    assert metadata.actor_attribution != metadata.trigger
    assert metadata.trigger != metadata.technical_provenance


# arid: enable
