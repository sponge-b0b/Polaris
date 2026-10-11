"""Pure drift classification over complete owner-attested current bases."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta

import pytest

from polaris.application.decisions.memory import DecisionMemoryService
from polaris.application.decisions.owner_meaning import DecisionOwnerMeaningReader
from polaris.application.evidence.context_versions import (
    ContextContribution,
    SelectedContextFact,
)
from polaris.application.evidence.current_basis import (
    BasisGuardRole,
    BasisPositiveRole,
    CurrentEvidenceBasis,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
    compare_current_evidence_bases,
)
from polaris.application.evidence.judgment_versions import ResolvedTargetJudgment
from polaris.application.evidence.owner_meaning import (
    CanonicalContextMeaning,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
)
from polaris.application.evidence.reconstruction import (
    EvidenceHistories,
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from polaris.domain.decisions import DecisionApplicability, DecisionWorkPosture
from polaris.domain.evidence import (
    ClaimCatalogVersion,
    EvidenceSupportVersion,
    EvidenceUse,
)
from polaris.domain.evidence.context_versions import (
    CanonicalContextVersionRef,
    ContextSelectionRole,
    DecisionAlternativeRevision,
)
from polaris.domain.evidence.judgment_versions import (
    InvestmentRecommendationVersionRef,
    JudgmentRevision,
)
from polaris.domain.evidence.sufficiency import (
    EvidenceSufficiencyResult,
    evaluate_evidence_sufficiency,
)
from tests.application.decisions.test_memory import _future_relationship_owner
from tests.application.evidence.test_context_versions import _OWNER_FAMILY_CASES
from tests.application.evidence.test_current_basis import (
    AT,
    _claim_scope,
    _complete_current,
    _empty_query,
    _future_withdrawn_decision,
    _query,
    _read_later,
    _selected_alternative,
)
from tests.configuration_support import (
    SECOND_VERSION_ID,
    requirement_key,
    requirement_version,
)


def _stale(
    prior: CurrentEvidenceBasis, fresh: CurrentEvidenceBasis | CurrentEvidenceNoBasis
) -> StaleEvidenceBasis:
    result = compare_current_evidence_bases(prior, fresh)
    assert isinstance(result, StaleEvidenceBasis)
    return result


def _assert_invalid_history(result: object) -> None:
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def _empty_bases() -> tuple[CurrentEvidenceBasis, CurrentEvidenceBasis]:
    query, key, target, *_ = _empty_query(requirement_key())
    return (
        _complete_current(query, key),
        _read_later(query, key, target, AT + timedelta(seconds=1)),
    )


def test_lawful_same_version_decision_change_returns_attested_decision_drift() -> None:
    query, key, target, _, _, _ = _query(
        decision=_future_withdrawn_decision(effective_at=AT + timedelta(seconds=1)),
        histories=EvidenceHistories((), (), ()),
        empty=True,
    )
    prior = _complete_current(query, key)
    later = AT + timedelta(seconds=1)
    fresh = _read_later(query, key, target, later)

    drift = _stale(prior, fresh)
    assert prior.decision.version == fresh.decision.version
    # duplicate-code: keep Decision posture explicit in this separate classifier proof.
    # arid: disable
    assert (
        prior.owner_meaning.decision.meaning.work_posture is DecisionWorkPosture.ACTIVE
    )
    assert fresh.owner_meaning.decision.meaning.work_posture is (
        DecisionWorkPosture.WITHDRAWN
    )
    # arid: enable
    assert drift.categories == {StaleEvidenceBasisCategory.DECISION_CHANGED}
    assert len(drift.changed_owner_meanings) == 1
    assert drift.changed_owner_meanings[0].role is BasisPositiveRole.DECISION
    assert drift.changed_owner_meanings[0].prior is prior.owner_meaning.decision
    assert drift.changed_owner_meanings[0].fresh is fresh.owner_meaning.decision
    assert drift.changed_positive_references == ()


def test_nonoperative_same_version_decision_is_decision_drift() -> None:
    decision, _, reader, *_ = _future_relationship_owner(
        effective_at=AT + timedelta(seconds=1)
    )
    query, key, target, _, _, _ = _query(
        decision=decision,
        histories=EvidenceHistories((), (), ()),
        empty=True,
    )
    query._decisions = DecisionMemoryService(reader=reader)
    query._decision_meaning = OwnerMeaningResolver(DecisionOwnerMeaningReader(reader))
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert fresh.owner_meaning.decision.meaning.applicability is (
        DecisionApplicability.NON_OPERATIVE
    )
    assert drift.categories == {StaleEvidenceBasisCategory.DECISION_CHANGED}


def test_independent_evidence_freshness_adds_time_to_decision_drift() -> None:
    query, key, target, _, _, _ = _query(decision=_future_withdrawn_decision())
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(days=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {
        StaleEvidenceBasisCategory.DECISION_CHANGED,
        StaleEvidenceBasisCategory.SUPPORT_CHANGED_BY_TIME,
    }
    assert prior.support_version == fresh.support_version
    assert prior.evaluation != fresh.evaluation


def test_same_version_target_claim_and_context_meanings_map_by_role() -> None:
    application_key, membership = _claim_scope(1)
    query, key, target, contexts, _, _ = _empty_query(
        application_key, claim_result=membership
    )
    selected = _selected_alternative()
    contexts.selected[ContextSelectionRole.SELECTED_ALTERNATIVE] = (selected,)
    prior = _complete_current(query, key)
    later = AT + timedelta(seconds=1)
    # duplicate-code: timed target meaning is local to this cross-read proof.
    # arid: disable
    owner = query._target_meaning._owner
    owner.future_fact_at = later
    owner.meaning_at[prior.owner_meaning.target.subject] = (
        later,
        "target now operative",
    )
    # arid: enable
    assert prior.owner_meaning.claim is not None
    owner.meaning_at[prior.owner_meaning.claim.subject] = (
        later,
        "claim now qualified",
    )
    context_proof = next(
        item
        for item in prior.owner_meaning.context
        if isinstance(item.subject, CanonicalContextMeaning)
    )
    owner.meaning_at[context_proof.subject] = (later, "context now operative")
    fresh = _read_later(query, key, target, later)

    drift = _stale(prior, fresh)
    assert drift.categories == {
        StaleEvidenceBasisCategory.TARGET_CHANGED,
        StaleEvidenceBasisCategory.CLAIM_CHANGED,
        StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
    }
    assert {item.role for item in drift.changed_owner_meanings} == {
        BasisPositiveRole.TARGET,
        BasisPositiveRole.CLAIM,
        BasisPositiveRole.CONTEXT,
    }
    assert all(
        item.prior.subject == item.fresh.subject
        and item.prior.cause.complete
        and item.fresh.cause.complete
        for item in drift.changed_owner_meanings
    )
    assert drift.changed_positive_references == ()


def test_claim_catalog_change_returns_typed_reference_and_membership_guard() -> None:
    application_key, membership = _claim_scope(1)
    query, key, target, _, _, _ = _empty_query(application_key, claim_result=membership)
    prior = _complete_current(query, key)
    newer = ClaimCatalogVersion(2)
    query._claims.result = replace(membership, catalog_version=newer)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {
        StaleEvidenceBasisCategory.CLAIM_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
    }
    assert any(
        item.role is BasisPositiveRole.CLAIM
        and item.prior == membership.catalog_version
        and item.fresh == newer
        for item in drift.changed_positive_references
    )
    assert any(
        item.role is BasisGuardRole.CLAIM_MEMBERSHIP for item in drift.broken_guards
    )


def test_target_version_and_support_epoch_changes_keep_exact_references() -> None:
    query, key, target, _, epochs, _ = _empty_query(requirement_key())
    prior = _complete_current(query, key)
    assert isinstance(target.result, ResolvedTargetJudgment)
    target.result = replace(
        target.result,
        version=InvestmentRecommendationVersionRef(key.target, JudgmentRevision(2)),
    )
    epochs.version = EvidenceSupportVersion(2)
    query._sufficiency.version = epochs.version
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {
        StaleEvidenceBasisCategory.TARGET_CHANGED,
        StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
    }
    assert {item.role for item in drift.changed_positive_references} == {
        BasisPositiveRole.TARGET,
        BasisPositiveRole.EVIDENCE_SUPPORT,
    }
    assert {item.prior for item in drift.changed_positive_references} == {
        prior.target.version,
        prior.support_version,
    }


def test_context_replacement_reports_positive_and_broken_selection_guard() -> None:
    # duplicate-code: local selection setup exposes the separate guard behavior.
    # arid: disable
    query, key, target, contexts, _, _ = _empty_query(requirement_key())
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    contexts.selected[role] = (_selected_alternative(),)
    prior = _complete_current(query, key)
    # arid: enable
    contexts.selected[role] = (_selected_alternative(),)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {
        StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
    }
    assert {item.role for item in drift.changed_positive_references} == {
        BasisPositiveRole.CONTEXT
    }
    assert any(
        item.role is BasisGuardRole.CONTEXT_SELECTION for item in drift.broken_guards
    )


def test_context_revision_drift_uses_positive_ref_without_broken_guard() -> None:
    query, key, target, contexts, _, _ = _empty_query(requirement_key())
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    original = _selected_alternative()
    contexts.selected[role] = (original,)
    prior = _complete_current(query, key)
    newer = replace(original.reference, revision=DecisionAlternativeRevision(2))
    contexts.selected[role] = (replace(original, reference=newer),)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
    assert drift.changed_positive_references[0].prior == original.reference
    assert drift.changed_positive_references[0].fresh == newer
    assert drift.broken_guards == ()
    assert prior.support_version == fresh.support_version


@pytest.mark.parametrize(("role", "reference"), _OWNER_FAMILY_CASES)
def test_each_context_family_attested_meaning_change_maps_to_evidence_support(
    role: ContextSelectionRole, reference: CanonicalContextVersionRef
) -> None:
    query, key, target, contexts, _, _ = _empty_query(requirement_key())
    # duplicate-code: each family stays explicit in this comparison proof.
    # arid: disable
    contexts.selected[role] = (
        SelectedContextFact(
            reference,
            "owner fact",
            "lineage",
            "applicable",
            "source",
            frozenset({ContextContribution.SUPPORT}),
        ),
    )
    # arid: enable
    prior = _complete_current(query, key)
    proof = next(
        item
        for item in prior.owner_meaning.context
        if isinstance(item.subject, CanonicalContextMeaning)
    )
    owner = query._context_meaning._owner
    later = AT + timedelta(seconds=1)
    owner.future_fact_at = later
    owner.meaning_at[proof.subject] = (later, "new owner meaning")
    fresh = _read_later(query, key, target, later)

    drift = _stale(prior, fresh)
    assert drift.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
    assert drift.changed_positive_references == ()
    assert len(drift.changed_owner_meanings) == 1
    assert drift.changed_owner_meanings[0].role is BasisPositiveRole.CONTEXT
    assert drift.changed_owner_meanings[0].prior.subject.reference == reference


def test_selection_guard_change_without_positive_drift_is_negative_only() -> None:
    query, key, target, contexts, _, _ = _empty_query(requirement_key())
    prior = _complete_current(query, key)
    contexts.revision += 1
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN}
    assert drift.changed_positive_references == ()
    assert drift.changed_owner_meanings == ()


def test_time_only_fitness_is_independent_of_decision_meaning() -> None:
    query, key, target, _, _, _ = _query()
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(days=1))

    drift = _stale(prior, fresh)
    assert drift.categories == {StaleEvidenceBasisCategory.SUPPORT_CHANGED_BY_TIME}
    assert drift.changed_owner_meanings == ()


def test_equal_semantic_witnesses_and_future_only_facts_do_not_stale() -> None:
    query, key, target, *_ = _empty_query(requirement_key())
    owner = query._target_meaning._owner
    owner.future_fact_at = AT + timedelta(days=1)
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))

    assert prior.owner_meaning.target.read_at != fresh.owner_meaning.target.read_at
    assert (
        prior.owner_meaning.target.semantic_identity
        == fresh.owner_meaning.target.semantic_identity
    )
    assert compare_current_evidence_bases(prior, fresh) is None


@pytest.mark.parametrize("reason", tuple(CurrentNoBasisReason))
def test_every_fresh_no_basis_reason_remains_distinct(
    reason: CurrentNoBasisReason,
) -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)
    result = CurrentEvidenceNoBasis(key, AT + timedelta(seconds=1), reason, "owner")
    assert compare_current_evidence_bases(prior, result) is result


def test_prior_must_be_complete_and_fresh_key_must_match() -> None:
    query, key, *_ = _query()
    prior = _complete_current(query, key)
    unusable = CurrentEvidenceNoBasis(key, AT, CurrentNoBasisReason.MISSING, "owner")
    with pytest.raises(TypeError, match="complete CurrentEvidenceBasis"):
        compare_current_evidence_bases(unusable, prior)  # type: ignore[arg-type]
    wrong_key = replace(key, use=EvidenceUse.CHALLENGE_BASIS)
    with pytest.raises(ValueError, match="same key"):
        compare_current_evidence_bases(
            prior,
            CurrentEvidenceNoBasis(
                wrong_key,
                AT + timedelta(seconds=1),
                CurrentNoBasisReason.UNAVAILABLE,
                "owner",
            ),
        )


def test_immutable_configuration_change_under_one_version_is_invalid() -> None:
    prior, fresh = _empty_bases()
    authority = fresh.sufficiency.requirement_version
    altered = replace(
        authority, recorded_at=authority.recorded_at + timedelta(seconds=1)
    )
    fresh = replace(
        fresh, sufficiency=replace(fresh.sufficiency, requirement_version=altered)
    )
    result = compare_current_evidence_bases(prior, fresh)
    _assert_invalid_history(result)


def test_fabricated_time_only_fitness_is_invalid_history() -> None:
    prior, fresh = _empty_bases()
    invented = replace(
        fresh,
        evaluation=replace(
            fresh.evaluation,
            result=(
                EvidenceSufficiencyResult.SUFFICIENT
                if fresh.evaluation.result is not EvidenceSufficiencyResult.SUFFICIENT
                else EvidenceSufficiencyResult.INSUFFICIENT
            ),
        ),
    )

    result = compare_current_evidence_bases(prior, invented)
    _assert_invalid_history(result)


def test_unattested_target_projection_under_same_version_is_invalid() -> None:
    prior, fresh = _empty_bases()
    altered = replace(fresh, target=replace(fresh.target, assertion="new assertion"))

    result = compare_current_evidence_bases(prior, altered)
    _assert_invalid_history(result)


def test_unattested_context_projection_under_same_reference_is_invalid() -> None:
    query, key, target, contexts, _, _ = _empty_query(requirement_key())
    role = ContextSelectionRole.SELECTED_ALTERNATIVE
    contexts.selected[role] = (_selected_alternative(),)
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))
    selected = next(item for item in fresh.context.selections if item.role is role)
    altered = replace(
        fresh,
        context=replace(
            fresh.context,
            selections=tuple(
                replace(item, facts=(replace(item.facts[0], fact="unattested"),))
                if item.role is role
                else item
                for item in fresh.context.selections
            ),
        ),
    )
    assert selected.facts[0] != next(
        item.facts[0] for item in altered.context.selections if item.role is role
    )

    result = compare_current_evidence_bases(prior, altered)
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_immutable_evidence_root_change_is_invalid_even_after_time_passes() -> None:
    query, key, target, *_ = _query()
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))
    observation = fresh.evidence.observations[0]
    altered = replace(
        observation,
        root=replace(
            observation.root,
            material=replace(
                observation.root.material,
                retained_representation="changed material",
            ),
        ),
    )
    fresh = replace(
        fresh,
        evidence=replace(fresh.evidence, observations=(altered,)),
    )

    result = compare_current_evidence_bases(prior, fresh)
    assert isinstance(result, CurrentEvidenceNoBasis)
    assert result.reason is CurrentNoBasisReason.INVALID_HISTORY


def test_public_stale_vocabulary_has_exactly_seven_categories() -> None:
    assert set(StaleEvidenceBasisCategory) == {
        StaleEvidenceBasisCategory.DECISION_CHANGED,
        StaleEvidenceBasisCategory.TARGET_CHANGED,
        StaleEvidenceBasisCategory.CLAIM_CHANGED,
        StaleEvidenceBasisCategory.REQUIREMENTS_CHANGED,
        StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
        StaleEvidenceBasisCategory.SUPPORT_CHANGED_BY_TIME,
    }


def test_requirement_version_changes_map_to_requirements_category() -> None:
    query, key, target, *_ = _empty_query(requirement_key())
    prior = _complete_current(query, key)
    fresh = _read_later(query, key, target, AT + timedelta(seconds=1))
    new_authority = requirement_version(SECOND_VERSION_ID)
    new_guard = replace(
        fresh.sufficiency.guards.requirement_authority,
        version_ids=frozenset({new_authority.version_id}),
    )
    fresh = replace(
        fresh,
        sufficiency=replace(
            fresh.sufficiency,
            requirement_version=new_authority,
            guards=replace(fresh.sufficiency.guards, requirement_authority=new_guard),
        ),
    )
    fresh = replace(
        fresh,
        evaluation=evaluate_evidence_sufficiency(
            fresh.sufficiency.requirement_version,
            fresh.requirement_key,
            fresh.sufficiency.interpretations,
            effective_at=fresh.at,
            known_at=fresh.at,
        ),
    )
    drift = _stale(prior, fresh)
    assert StaleEvidenceBasisCategory.REQUIREMENTS_CHANGED in drift.categories
    assert any(
        item.role is BasisPositiveRole.REQUIREMENT
        and item.prior == prior.sufficiency.requirement_version.version_id
        and item.fresh == new_authority.version_id
        for item in drift.changed_positive_references
    )


def test_invalid_future_only_history_passes_through_without_stale() -> None:
    query, key, target, _, _, store = _query(decision=_future_withdrawn_decision())
    prior = _complete_current(query, key)
    # duplicate-code: comparator proof retains its own malformed history setup.
    # arid: disable
    initiation, future = store.decision.history
    store.history_override = (
        initiation,
        replace(
            future,
            metadata=replace(future.metadata, fact_id=initiation.metadata.fact_id),
        ),
    )
    # arid: enable
    fresh = asyncio.run(query.read(key, at=AT + timedelta(seconds=1)))
    assert isinstance(fresh, CurrentEvidenceNoBasis)
    assert fresh.reason is CurrentNoBasisReason.INVALID_HISTORY
    assert compare_current_evidence_bases(prior, fresh) is fresh


def test_unverified_downstream_cause_is_no_basis_before_comparison() -> None:
    query, key, target, *_ = _query()
    prior = _complete_current(query, key)
    owner = query._target_meaning._owner
    owner.failure = OwnerMeaningNoBasisReason.CONTRADICTORY
    owner.failure_for = type(prior.owner_meaning.target.subject)
    fresh = asyncio.run(query.read(key, at=AT))
    assert isinstance(fresh, CurrentEvidenceNoBasis)
    assert fresh.reason is CurrentNoBasisReason.CONTRADICTORY
    assert compare_current_evidence_bases(prior, fresh) is fresh
