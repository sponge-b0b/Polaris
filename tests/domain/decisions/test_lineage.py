"""Complete known-timeline admission through the public relationship boundary."""

from dataclasses import dataclass, fields
from datetime import datetime
from itertools import permutations
from re import escape
from uuid import uuid4

import pytest

from polaris.domain.decisions import (
    DecisionLifecycleFactId,
    DecisionLifecycleLineageCycle,
    DecisionLifecycleLineageSafetyIndeterminate,
    DecisionRelationshipCorrected,
    DecisionRelationshipFact,
    DecisionRelationshipFactId,
    DecisionRelationshipState,
    DecisionVersion,
    InvalidDecisionIdentity,
    InvalidDecisionRelationshipHistory,
    InvestmentDecisionId,
    OperationId,
    RenewedFromRelationshipBasis,
    TechnicalReference,
    TechnicalReferenceKind,
    apply_relationship_command,
    relationship_fact,
    validate_decision_lifecycle_lineage,
)
from tests.domain.decisions.test_relationships import (
    DISCONFIRM,
    OPERATIVE,
    QUALIFY,
    RENEWED_FROM,
    SUPERSEDES,
    DecisionRelationshipCorrectionBasis,
    SupersedesRelationshipBasis,
    apply,
    at,
    initiate,
    query,
    relationship_correction,
    relationship_mutation,
    resolve,
    supersedes,
    unsupported,
)


def correction(target, *, recorded, active, replacement=None, operation_id=None):
    return relationship_correction(
        target_relationship_fact_id=target.metadata.relationship_fact_id,
        effect=DISCONFIRM if replacement is None else QUALIFY,
        correction_effective_at=at(active),
        correction_basis=DecisionRelationshipCorrectionBasis(["correct lineage"]),
        replacement_relationship_effective_at=(
            None if replacement is None else at(replacement)
        ),
        replacement_relationship_basis=(
            None
            if replacement is None
            else SupersedesRelationshipBasis(["replacement"])
        ),
        mutation=relationship_mutation(recorded, operation_id=operation_id),
    )


@pytest.mark.parametrize("effective", [0, 10, 100_000_000])
@pytest.mark.parametrize("length", [2, 3, 5])
def test_command_rejects_complete_historical_current_and_distant_future_cycles(
    effective, length
):
    decisions = [initiate() for _ in range(length)]
    edges = [
        supersedes(decisions[i], decisions[i + 1], effective=effective, recorded=1)
        for i in range(length - 1)
    ]
    closing = supersedes(decisions[-1], decisions[0], effective=effective, recorded=10)
    with pytest.raises(
        DecisionLifecycleLineageCycle, match=escape(at(effective).isoformat())
    ):
        apply(edges, [closing], {d.decision_id: d for d in decisions}, boundary=10)
    assert len(edges) == length - 1
    assert all(d.version == DecisionVersion(1) for d in decisions)


@pytest.mark.parametrize("kind", [SUPERSEDES, RENEWED_FROM])
@pytest.mark.parametrize("effective", [0, 100_000_000])
def test_self_reference_is_a_typed_definite_cycle(kind, effective):
    decision = initiate()
    basis = (
        SupersedesRelationshipBasis(["self"])
        if kind == SUPERSEDES
        else RenewedFromRelationshipBasis(["self"])
    )
    with pytest.raises(DecisionLifecycleLineageCycle):
        relationship_fact(
            source_decision_id=decision.decision_id,
            target_decision_id=decision.decision_id,
            relationship_type=kind,
            relationship_effective_at=at(effective),
            relationship_basis=basis,
            mutation=relationship_mutation(10),
        )


@pytest.mark.parametrize("effective", [3, 4, 100_000_000])
def test_mixed_type_cycle_uses_direction_across_both_types(effective):
    old = resolve(initiate(), recorded=1)
    new = initiate(recorded=2, effective=2)
    renewal = relationship_fact(
        source_decision_id=new.decision_id,
        target_decision_id=old.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(3),
        relationship_basis=RenewedFromRelationshipBasis(["renewed judgment"]),
        mutation=relationship_mutation(3),
    )
    admitted = apply([], [renewal], {d.decision_id: d for d in (old, new)}, boundary=3)
    reverse = supersedes(old, new, effective=effective, recorded=4)
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply(
            admitted.history,
            [reverse],
            {d.decision_id: d for d in admitted.updated_decisions},
            boundary=4,
        )


def test_historical_cycle_cannot_hide_behind_current_withdrawal():
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=1, recorded=1)
    withdraw = correction(ab, recorded=3, active=3)
    ba = supersedes(b, a, effective=2, recorded=4)
    assert query([ab, withdraw], a, b, 4).state == DecisionRelationshipState.WITHDRAWN
    with pytest.raises(DecisionLifecycleLineageCycle, match=escape(at(2).isoformat())):
        apply([ab, withdraw], [ba], {a.decision_id: a, b.decision_id: b}, boundary=4)


def test_not_effective_explanatory_support_is_not_an_edge_and_adjacent_intervals_pass():
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=0, recorded=1)
    replace = correction(ab, recorded=2, active=5, replacement=30)
    stop = correction(replace, recorded=3, active=25)
    # Restoring the original at 25 creates A->B then, but never during [5,20).
    ba = supersedes(b, a, effective=5, recorded=4)
    end_ba = correction(
        ba, recorded=4, active=20, operation_id=ba.metadata.operation_id
    )
    view = query([ab, replace, stop], a, b, 5, 4)
    assert view.state == DecisionRelationshipState.NOT_EFFECTIVE
    assert view.support_fact_ids
    result = apply(
        [ab, replace, stop],
        [ba, end_ba],
        {a.decision_id: a, b.decision_id: b},
        boundary=4,
    )
    validate_decision_lifecycle_lineage(result.history, known_at=at(4))


def test_contested_positive_edges_are_conservative_without_blanket_rejection():
    a, b, c = initiate(), initiate(), initiate()
    ab = supersedes(a, b, effective=0, recorded=0)
    one = correction(ab, recorded=1, active=1, replacement=1)
    two = correction(ab, recorded=2, active=1, replacement=2)
    history = [ab, one, two]
    view = query(history, a, b, 3)
    assert view.state == DecisionRelationshipState.CONTESTED
    assert len(view.surviving_positive_claims) == 2
    bc = supersedes(b, c, effective=3, recorded=3)
    result = apply(history, [bc], {d.decision_id: d for d in (a, b, c)}, boundary=3)
    ca = supersedes(c, a, effective=100_000_000, recorded=4)
    with pytest.raises(DecisionLifecycleLineageSafetyIndeterminate):
        apply(result.history, [ca], {d.decision_id: d for d in (a, b, c)}, boundary=4)


def test_supported_cycle_stays_definite_beside_unrelated_contest():
    a, b, c, d = [initiate() for _ in range(4)]
    cd = supersedes(c, d, effective=0, recorded=0)
    one = correction(cd, recorded=1, active=1, replacement=1)
    two = correction(cd, recorded=2, active=1, replacement=2)
    ab = supersedes(a, b, effective=3, recorded=3)
    ba = supersedes(b, a, effective=3, recorded=4)
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply(
            [cd, one, two, ab],
            [ba],
            {x.decision_id: x for x in (a, b, c, d)},
            boundary=4,
        )


@pytest.mark.parametrize("action", ["qualify", "restore", "recursive-restore"])
def test_every_correction_path_rechecks_final_history(action):
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=10, recorded=1)
    ba = supersedes(b, a, effective=0, recorded=1)
    end_ba = correction(ba, recorded=2, active=10)
    history = [ab, ba, end_ba]
    if action == "qualify":
        proposed = correction(ab, recorded=5, active=3, replacement=3)
    elif action == "restore":
        proposed = correction(end_ba, recorded=5, active=10)
    else:
        defeated = correction(end_ba, recorded=3, active=10)
        restored = correction(defeated, recorded=4, active=10)
        history.extend([defeated, restored])
        proposed = correction(restored, recorded=5, active=10)
    validate_decision_lifecycle_lineage(history, known_at=at(4))
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply(history, [proposed], {a.decision_id: a, b.decision_id: b}, boundary=5)


def test_atomic_repair_accepts_only_final_history_independent_of_serialization_order():
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=10, recorded=1)
    ba = supersedes(b, a, effective=0, recorded=1)
    end_ba = correction(ba, recorded=2, active=10)
    before = (ab, ba, end_ba)
    operation = OperationId(uuid4())
    restore_ba = correction(end_ba, recorded=3, active=10, operation_id=operation)
    stop_ab = correction(ab, recorded=3, active=10, operation_id=operation)
    decisions = {a.decision_id: a, b.decision_id: b}
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply(before, [restore_ba], decisions, boundary=3)
    for batch in permutations([restore_ba, stop_ab]):
        result = apply(before, batch, decisions, boundary=3)
        assert set(result.history) == {*before, *batch}
        assert (
            query(result.history, a, b, 10, 3).state
            == DecisionRelationshipState.WITHDRAWN
        )
        assert (
            query(result.history, b, a, 10, 3).state
            == DecisionRelationshipState.SUPPORTED
        )
    assert before == (ab, ba, end_ba)
    assert a.version == b.version == DecisionVersion(1)


@pytest.mark.parametrize("effective", [0, 10, 100_000_000])
def test_many_to_many_diamond_is_acyclic(effective):
    a, b, c, d = [initiate() for _ in range(4)]
    operation = OperationId(uuid4())
    edges = [
        supersedes(
            source, target, effective=effective, recorded=10, operation_id=operation
        )
        for source, target in [(a, b), (a, c), (b, d), (c, d)]
    ]
    result = apply([], edges, {x.decision_id: x for x in (a, b, c, d)}, boundary=10)
    for ordering in (result.history, tuple(reversed(result.history))):
        validate_decision_lifecycle_lineage(ordering, known_at=at(10))


def test_known_boundary_excludes_later_knowledge_but_missing_ancestry_fails():
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=0, recorded=1)
    ba = supersedes(b, a, effective=0, recorded=10)
    validate_decision_lifecycle_lineage([ab, ba], known_at=at(9))
    with pytest.raises(DecisionLifecycleLineageCycle):
        validate_decision_lifecycle_lineage([ab, ba], known_at=at(10))
    orphan = correction(ab, recorded=2, active=100_000_000)
    with pytest.raises(
        InvalidDecisionRelationshipHistory, match="complete target ancestry"
    ):
        validate_decision_lifecycle_lineage([orphan], known_at=at(2))
    with pytest.raises(InvalidDecisionRelationshipHistory, match="globally unique"):
        validate_decision_lifecycle_lineage([ab, ab], known_at=at(2))


def test_non_endpoint_future_path_invalidates_graph_without_version_change():
    a, b, c, d = [initiate() for _ in range(4)]
    ad = supersedes(a, d, effective=1000, recorded=1)
    cb = supersedes(c, b, effective=1000, recorded=1)
    ba = supersedes(b, a, effective=1000, recorded=3)
    endpoints = {a.decision_id: a, b.decision_id: b}
    candidate = apply([ad, cb], [ba], endpoints, boundary=3)
    assert not candidate.versioned_decision_ids
    requirements = candidate.protection_requirements
    assert requirements.requires_complete_relationship_history
    assert requirements.requires_graph_revalidation
    assert requirements.requires_absence_revalidation
    assert requirements.recording_boundary == at(3)
    dc = supersedes(d, c, effective=1000, recorded=2)
    concurrent = apply([ad, cb], [dc], {d.decision_id: d, c.decision_id: c}, boundary=2)
    assert not concurrent.versioned_decision_ids
    # Endpoint versions match, but the authoritative full predicate changed.
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply_relationship_command(
            concurrent.history,
            [ba],
            decisions=endpoints,
            expected_versions={x: value.version for x, value in endpoints.items()},
            recording_boundary=at(3),
        )


def test_endpoint_lifecycle_changes_do_not_delete_admitted_edges():
    a, b, c = initiate(), initiate(), initiate()
    ab = supersedes(a, b, effective=1, recorded=1)
    bc = supersedes(b, c, effective=1, recorded=1)
    b_now = unsupported(b, recorded=2)
    ca = supersedes(c, a, effective=3, recorded=3)
    with pytest.raises(DecisionLifecycleLineageCycle):
        apply([ab, bc], [ca], {d.decision_id: d for d in (a, b_now, c)}, boundary=3)


@pytest.mark.parametrize("kind", list(TechnicalReferenceKind))
def test_graph_boundary_rejects_technical_identity_and_retrieval_values(kind):
    technical = TechnicalReference(kind, "technical-id")
    with pytest.raises(InvalidDecisionRelationshipHistory):
        validate_decision_lifecycle_lineage([technical], known_at=at(1))
    a = initiate()
    with pytest.raises(InvalidDecisionIdentity):
        relationship_fact(
            source_decision_id=technical,
            target_decision_id=a.decision_id,
            relationship_type=SUPERSEDES,
            relationship_effective_at=at(1),
            relationship_basis=SupersedesRelationshipBasis(["basis"]),
            mutation=relationship_mutation(1),
        )
    with pytest.raises(InvalidDecisionIdentity):
        relationship_correction(
            target_relationship_fact_id=technical,
            effect=DISCONFIRM,
            correction_effective_at=at(1),
            correction_basis=DecisionRelationshipCorrectionBasis(["correction"]),
            mutation=relationship_mutation(1),
        )


def test_future_context_shape_keeps_exact_target_history_separate_from_lineage():
    # A test-only future purpose-specific shape, not a production context command.
    @dataclass(frozen=True)
    class MaterialPriorDecisionContextExample:
        source_decision_id: InvestmentDecisionId
        target_decision_id: InvestmentDecisionId
        target_as_known_at: datetime
        target_version: DecisionVersion
        target_fact_ids: frozenset[DecisionLifecycleFactId]

    source, target, other = initiate(), initiate(), initiate()
    retrieved = (target, other)
    original_history = source.history
    selected = retrieved[0]
    used = MaterialPriorDecisionContextExample(
        source.decision_id,
        selected.decision_id,
        at(0),
        selected.version,
        frozenset(f.metadata.fact_id for f in selected.history),
    )
    later = resolve(target, recorded=1)
    assert used.target_version != later.version
    assert used.target_fact_ids < frozenset(f.metadata.fact_id for f in later.history)
    assert (
        later.as_known_at(used.target_as_known_at, applicability=OPERATIVE).disposition
        == target.disposition
    )
    assert source.history == original_history
    for candidate in (*retrieved, used):
        with pytest.raises(InvalidDecisionRelationshipHistory):
            validate_decision_lifecycle_lineage([candidate], known_at=at(2))
    assert {f.name for f in fields(DecisionRelationshipFact)} == {
        "metadata",
        "source_decision_id",
        "target_decision_id",
        "relationship_type",
        "relationship_effective_at",
        "relationship_basis",
    }
    assert not any("context" in f.name for f in fields(DecisionRelationshipCorrected))
    assert set(type(SUPERSEDES)) == {SUPERSEDES, RENEWED_FROM}
    assert DecisionRelationshipFactId(uuid4()) != used.target_decision_id


def test_parallel_lineage_types_preserve_one_direction_without_false_cycle():
    old = resolve(initiate(), recorded=1)
    new = initiate(recorded=2, effective=2)
    operation = OperationId(uuid4())
    renewal = relationship_fact(
        source_decision_id=new.decision_id,
        target_decision_id=old.decision_id,
        relationship_type=RENEWED_FROM,
        relationship_effective_at=at(3),
        relationship_basis=RenewedFromRelationshipBasis(["renewal"]),
        mutation=relationship_mutation(3, operation_id=operation),
    )
    supersession = supersedes(new, old, effective=3, recorded=3, operation_id=operation)
    result = apply(
        [], [renewal, supersession], {d.decision_id: d for d in (old, new)}, boundary=3
    )
    assert {f.relationship_type for f in result.history} == {RENEWED_FROM, SUPERSEDES}
    assert len(result.history) == 2


def test_positive_withdrawal_contest_rejects_possible_cycle_at_activation_boundary():
    a, b = initiate(), initiate()
    ab = supersedes(a, b, effective=0, recorded=0)
    positive = correction(ab, recorded=1, active=10, replacement=10)
    withdrawal = correction(ab, recorded=2, active=10)
    reverse = supersedes(b, a, effective=10, recorded=3)
    view = query([ab, positive, withdrawal], a, b, 10, 3)
    assert view.state == DecisionRelationshipState.CONTESTED
    assert len(view.surviving_positive_claims) == 1
    with pytest.raises(DecisionLifecycleLineageSafetyIndeterminate):
        apply(
            [ab, positive, withdrawal],
            [reverse],
            {a.decision_id: a, b.decision_id: b},
            boundary=3,
        )
