from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from polaris.domain.decisions.facts import DecisionVersion, InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextRootRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    DecisionAlternativeId,
    DecisionAlternativeRevision,
    DecisionAlternativeVersionRef,
    DecisionContextVersionRef,
    InvestmentAuthorityRegimeId,
    InvestmentAuthorityRegimeRevision,
    InvestmentAuthorityRegimeVersionRef,
    InvestmentMandateId,
    InvestmentMandateRevision,
    InvestmentMandateVersionRef,
    InvestmentStrategyId,
    InvestmentStrategyRevision,
    InvestmentStrategyVersionRef,
    OtherJudgmentContextVersionRef,
    OutcomeId,
    OutcomeRevision,
    OutcomeVersionRef,
    PortfolioBoundaryId,
    PortfolioBoundaryRevision,
    PortfolioBoundaryVersionRef,
    PortfolioStateId,
    PortfolioStateRevision,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateId,
    ProjectedPortfolioStateRevision,
    ProjectedPortfolioStateVersionRef,
    context_root,
    is_canonical_context_version_ref,
)
from polaris.domain.evidence.judgment_versions import (
    InvestmentViewVersionRef,
    JudgmentRevision,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
)


def _key() -> BasisScopeKey:
    return BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        InvestmentViewRef(uuid4()),
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )


@dataclass(frozen=True, slots=True)
class SelectionWitness:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: ContextRootRef
    relationship_revision: int


@dataclass(frozen=True, slots=True)
class SelectionUniverse:
    key: BasisScopeKey
    role: ContextSelectionRole
    relationship_revision: int


def _guard(
    key: BasisScopeKey,
    role: ContextSelectionRole,
    roots: frozenset[ContextRootRef],
    *,
    relationship_revision: int = 1,
    universe_revision: int = 1,
) -> ContextSelectionGuard:
    return ContextSelectionGuard(
        key,
        role,
        roots,
        frozenset(
            SelectionWitness(key, role, root, relationship_revision) for root in roots
        ),
        SelectionUniverse(key, role, universe_revision),
    )


_OWNED_FAMILIES = (
    (DecisionAlternativeId, DecisionAlternativeRevision, DecisionAlternativeVersionRef),
    (PortfolioBoundaryId, PortfolioBoundaryRevision, PortfolioBoundaryVersionRef),
    (PortfolioStateId, PortfolioStateRevision, PortfolioStateVersionRef),
    (
        ProjectedPortfolioStateId,
        ProjectedPortfolioStateRevision,
        ProjectedPortfolioStateVersionRef,
    ),
    (InvestmentMandateId, InvestmentMandateRevision, InvestmentMandateVersionRef),
    (InvestmentStrategyId, InvestmentStrategyRevision, InvestmentStrategyVersionRef),
    (
        InvestmentAuthorityRegimeId,
        InvestmentAuthorityRegimeRevision,
        InvestmentAuthorityRegimeVersionRef,
    ),
    (OutcomeId, OutcomeRevision, OutcomeVersionRef),
)


@pytest.mark.parametrize(("id_type", "revision_type", "ref_type"), _OWNED_FAMILIES)
def test_every_owner_family_has_distinct_positive_root_local_revision(
    id_type: type[object], revision_type: type[object], ref_type: type[object]
) -> None:
    root = id_type(uuid4())  # type: ignore[call-arg]
    first = ref_type(root, revision_type(1))  # type: ignore[call-arg]
    changed = ref_type(root, revision_type(2))  # type: ignore[call-arg]
    other_root = ref_type(id_type(uuid4()), revision_type(1))  # type: ignore[call-arg]
    assert is_canonical_context_version_ref(first)
    assert changed != first
    assert other_root != first
    assert not hasattr(first, "__dict__")
    for invalid in (0, -1, True, 1.0, "1"):
        with pytest.raises(ValueError, match="positive"):
            revision_type(invalid)  # type: ignore[call-arg]
    with pytest.raises(TypeError, match="revision"):
        ref_type(root, DecisionVersion(1))  # type: ignore[call-arg]


def test_decision_and_other_judgment_are_context_only_when_explicitly_wrapped() -> None:
    decision = DecisionContextVersionRef(
        InvestmentDecisionId(uuid4()), DecisionVersion(1)
    )
    judgment = InvestmentViewVersionRef(InvestmentViewRef(uuid4()), JudgmentRevision(1))
    assert is_canonical_context_version_ref(decision)
    assert is_canonical_context_version_ref(OtherJudgmentContextVersionRef(judgment))
    assert not is_canonical_context_version_ref(judgment)
    assert not is_canonical_context_version_ref(("portfolio_state", uuid4(), 1))


def test_selection_guard_is_typed_and_replacement_breaks_even_when_old_root_stays() -> (
    None
):
    key = _key()
    old = PortfolioStateVersionRef(PortfolioStateId(uuid4()), PortfolioStateRevision(1))
    new = PortfolioStateVersionRef(PortfolioStateId(uuid4()), PortfolioStateRevision(1))
    empty = _guard(key, ContextSelectionRole.ACTUAL_PORTFOLIO_STATE, frozenset())
    selected = _guard(
        key, ContextSelectionRole.ACTUAL_PORTFOLIO_STATE, frozenset({old.root})
    )
    replacement = _guard(
        key, ContextSelectionRole.ACTUAL_PORTFOLIO_STATE, frozenset({new.root})
    )
    assert empty != selected
    assert selected != replacement
    assert old.revision == new.revision
    assert selected == _guard(
        key,
        ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
        frozenset(
            {
                context_root(
                    PortfolioStateVersionRef(old.root, PortfolioStateRevision(2))
                )
            }
        ),
    )
    assert selected != _guard(
        key,
        ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
        frozenset({old.root}),
        relationship_revision=2,
    )
    assert empty != _guard(
        key,
        ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
        frozenset(),
        universe_revision=2,
    )
    with pytest.raises(TypeError, match="PortfolioStateId"):
        _guard(
            key,
            ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
            frozenset({OutcomeId(uuid4())}),
        )


def test_governing_decision_and_exact_target_cannot_be_context_selection() -> None:
    key = _key()
    with pytest.raises(ValueError, match="governing Decision"):
        _guard(
            key,
            ContextSelectionRole.USED_PRIOR_DECISION,
            frozenset({key.decision_id}),
        )
    with pytest.raises(ValueError, match="exact Evidence target"):
        _guard(
            key,
            ContextSelectionRole.OTHER_ADMITTED_JUDGMENT,
            frozenset({key.target}),
        )


def test_relationship_witness_is_required_and_scoped_to_exact_key() -> None:
    key = _key()
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    root = PortfolioStateId(uuid4())
    with pytest.raises(ValueError, match="requires a relationship witness"):
        ContextSelectionGuard(
            key, role, frozenset({root}), frozenset(), SelectionUniverse(key, role, 1)
        )
    with pytest.raises(ValueError, match="exact key, role and root"):
        ContextSelectionGuard(
            key,
            role,
            frozenset({root}),
            frozenset({SelectionWitness(_key(), role, root, 1)}),
            SelectionUniverse(key, role, 1),
        )
    with pytest.raises(ValueError, match="selection universe must match"):
        ContextSelectionGuard(
            key, role, frozenset(), frozenset(), SelectionUniverse(_key(), role, 1)
        )
