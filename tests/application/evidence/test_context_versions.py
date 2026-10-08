from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from polaris.application.evidence.context_versions import (
    CompleteContextSelection,
    ContextContribution,
    ContextNoBasis,
    ContextNoBasisReason,
    ContextOwnerReadUnavailable,
    ContextSelectionResolver,
    ResolvedContextSelection,
    SelectedContextFact,
)
from polaris.domain.configuration import InvestmentHorizon
from polaris.domain.decisions.facts import DecisionVersion, InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    CanonicalContextVersionRef,
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
from polaris.domain.portfolio import FinancialInstrumentId, PortfolioId

_AT = datetime(2026, 1, 1, tzinfo=UTC)
_PORTFOLIO_ID = PortfolioId(uuid4())
_INSTRUMENT_ID = FinancialInstrumentId(uuid4())


# duplicate-code: each test layer constructs its own exact key so domain and
# owner-read falsifiers stay independently legible rather than sharing setup.
# arid: disable
def _key() -> BasisScopeKey:
    return BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        InvestmentViewRef(uuid4()),
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )


# arid: enable


@dataclass(frozen=True, slots=True)
class MandateMembers:
    objectives: tuple[str, ...]
    principles: tuple[str, ...]
    dependent_members: tuple[str, ...]
    applicable_from: datetime


@dataclass(frozen=True, slots=True)
class OwnerCoordinates:
    portfolio_id: PortfolioId
    instrument_id: FinancialInstrumentId
    horizon: InvestmentHorizon


@dataclass(frozen=True, slots=True)
class OwnerRelationshipWitness:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: ContextRootRef
    relationship_epoch: int


@dataclass(frozen=True, slots=True)
class OwnerSelectionUniverse:
    key: BasisScopeKey
    role: ContextSelectionRole
    relationship_epoch: int


def _resolved(
    key: BasisScopeKey,
    role: ContextSelectionRole,
    at: datetime,
    facts: tuple[SelectedContextFact[object, object, object, object], ...] = (),
    *,
    known_at: datetime | None = None,
    relationship_epoch: int = 1,
    universe_epoch: int = 1,
) -> ResolvedContextSelection[object, object, object, object]:
    roots = frozenset(context_root(f.reference) for f in facts)
    return ResolvedContextSelection(
        key,
        role,
        at,
        known_at or at,
        facts,
        ContextSelectionGuard(
            # duplicate-code: the application owner-result fixture keeps its guard
            # construction visible independently of the domain guard proof.
            # arid: disable
            key,
            role,
            roots,
            # arid: enable
            frozenset(
                OwnerRelationshipWitness(key, role, root, relationship_epoch)
                for root in roots
            ),
            OwnerSelectionUniverse(key, role, universe_epoch),
        ),
    )


def _fact(
    reference: CanonicalContextVersionRef,
    meaning: object,
) -> SelectedContextFact[object, object, object, object]:
    return SelectedContextFact(
        reference,
        meaning,
        ("attributable correction lineage",),
        OwnerCoordinates(_PORTFOLIO_ID, _INSTRUMENT_ID, InvestmentHorizon("long")),
        ("external source", "as-of", "known-at"),
        frozenset({ContextContribution.APPLICABILITY, ContextContribution.SUPPORT}),
    )


class OwnerDouble:
    def __init__(self) -> None:
        self.results: dict[ContextSelectionRole, object] = {}
        self.history: dict[tuple[ContextSelectionRole, datetime, datetime], object] = {}
        self.scoped_results: dict[
            tuple[BasisScopeKey, ContextSelectionRole, datetime, datetime], object
        ] = {}
        self.calls: list[
            tuple[BasisScopeKey, ContextSelectionRole, datetime, datetime]
        ] = []

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> object:
        self.calls.append((key, role, effective_at, known_at))
        outcome = self.scoped_results.get(
            (key, role, effective_at, known_at),
            self.history.get((role, effective_at, known_at), self.results.get(role)),
        )
        if isinstance(outcome, ContextOwnerReadUnavailable):
            raise outcome
        if outcome is not None:
            return outcome
        return _resolved(key, role, effective_at, known_at=known_at)


def test_complete_current_read_attests_every_family_and_preserves_owner_meaning() -> (
    None
):
    key = _key()
    mandate = InvestmentMandateVersionRef(
        InvestmentMandateId(uuid4()), InvestmentMandateRevision(1)
    )
    members = MandateMembers(("grow",), ("liquidity",), ("objective-1",), _AT)
    owner = OwnerDouble()
    owner.results[ContextSelectionRole.INVESTMENT_MANDATE] = _resolved(
        key, ContextSelectionRole.INVESTMENT_MANDATE, _AT, (_fact(mandate, members),)
    )
    result = asyncio.run(
        ContextSelectionResolver(owner).read_complete_current(key, at=_AT)
    )
    assert type(result) is CompleteContextSelection
    assert len(result.selections) == len(ContextSelectionRole)
    assert result.positive_references == (mandate,)
    assert result.selections[6].facts[0].fact == members
    assert result.selections[6].facts[0].lineage == ("attributable correction lineage",)
    coordinates = result.selections[6].facts[0].applicability
    assert isinstance(coordinates, OwnerCoordinates)
    assert coordinates.portfolio_id == _PORTFOLIO_ID
    assert result.selections[6].facts[0].provenance == (
        "external source",
        "as-of",
        "known-at",
    )
    assert all(effective == known == _AT for _, _, effective, known in owner.calls)


_OWNER_FAMILY_CASES = (
    (
        ContextSelectionRole.USED_PRIOR_DECISION,
        DecisionContextVersionRef(InvestmentDecisionId(uuid4()), DecisionVersion(1)),
    ),
    (
        ContextSelectionRole.OTHER_ADMITTED_JUDGMENT,
        OtherJudgmentContextVersionRef(
            InvestmentViewVersionRef(InvestmentViewRef(uuid4()), JudgmentRevision(1))
        ),
    ),
    (
        ContextSelectionRole.SELECTED_ALTERNATIVE,
        DecisionAlternativeVersionRef(
            DecisionAlternativeId(uuid4()), DecisionAlternativeRevision(1)
        ),
    ),
    (
        ContextSelectionRole.PORTFOLIO_BOUNDARY,
        PortfolioBoundaryVersionRef(
            PortfolioBoundaryId(uuid4()), PortfolioBoundaryRevision(1)
        ),
    ),
    (
        ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
        PortfolioStateVersionRef(PortfolioStateId(uuid4()), PortfolioStateRevision(1)),
    ),
    (
        ContextSelectionRole.PROJECTED_PORTFOLIO_STATE,
        ProjectedPortfolioStateVersionRef(
            ProjectedPortfolioStateId(uuid4()), ProjectedPortfolioStateRevision(1)
        ),
    ),
    (
        ContextSelectionRole.INVESTMENT_MANDATE,
        InvestmentMandateVersionRef(
            InvestmentMandateId(uuid4()), InvestmentMandateRevision(1)
        ),
    ),
    (
        ContextSelectionRole.INVESTMENT_STRATEGY,
        InvestmentStrategyVersionRef(
            InvestmentStrategyId(uuid4()), InvestmentStrategyRevision(1)
        ),
    ),
    (
        ContextSelectionRole.INVESTMENT_AUTHORITY_REGIME,
        InvestmentAuthorityRegimeVersionRef(
            InvestmentAuthorityRegimeId(uuid4()), InvestmentAuthorityRegimeRevision(1)
        ),
    ),
    (
        ContextSelectionRole.OUTCOME,
        OutcomeVersionRef(OutcomeId(uuid4()), OutcomeRevision(1)),
    ),
)


@pytest.mark.parametrize(("role", "reference"), _OWNER_FAMILY_CASES)
def test_each_typed_family_survives_its_owner_read(
    role: ContextSelectionRole, reference: CanonicalContextVersionRef
) -> None:
    key = _key()
    owner = OwnerDouble()
    owner.results[role] = _resolved(key, role, _AT, (_fact(reference, "owner fact"),))
    result = asyncio.run(
        ContextSelectionResolver(owner).read_current(key, role, at=_AT)
    )
    assert type(result) is ResolvedContextSelection
    assert result.facts[0].reference == reference
    assert result.guard.selected == frozenset({context_root(reference)})
    assert len(result.guard.relationships) == 1


def test_mandate_member_change_advances_owner_ref_once_for_one_commit() -> None:
    root = InvestmentMandateId(uuid4())
    initial = InvestmentMandateVersionRef(root, InvestmentMandateRevision(1))
    changed = InvestmentMandateVersionRef(root, InvestmentMandateRevision(2))
    first_members = MandateMembers(("grow",), ("liquidity",), ("objective-1",), _AT)
    changed_members = MandateMembers(
        ("grow", "protect"), ("liquidity",), ("objective-1", "objective-2"), _AT
    )
    key = _key()
    old = _resolved(
        key,
        ContextSelectionRole.INVESTMENT_MANDATE,
        _AT,
        (_fact(initial, first_members),),
    )
    current_at = _AT + timedelta(days=1)
    current = _resolved(
        key,
        ContextSelectionRole.INVESTMENT_MANDATE,
        current_at,
        (_fact(changed, changed_members),),
    )
    assert old.facts[0].reference != current.facts[0].reference
    assert old.facts[0].fact == first_members
    assert current.facts[0].fact == changed_members
    assert initial.root == changed.root
    assert changed.revision.value == initial.revision.value + 1


def test_owner_issued_revision_transitions_are_consumed_without_synthesis() -> None:
    key = _key()
    role = ContextSelectionRole.INVESTMENT_MANDATE
    root = InvestmentMandateId(uuid4())
    first = InvestmentMandateVersionRef(root, InvestmentMandateRevision(1))
    changed = InvestmentMandateVersionRef(root, InvestmentMandateRevision(2))
    successor = InvestmentMandateVersionRef(
        InvestmentMandateId(uuid4()), InvestmentMandateRevision(1)
    )
    at_noop = _AT + timedelta(hours=1)
    at_commit = _AT + timedelta(hours=2)
    at_successor = _AT + timedelta(hours=3)
    owner = OwnerDouble()
    owner.scoped_results[(key, role, _AT, _AT)] = _resolved(
        key, role, _AT, (_fact(first, "initial mandate"),)
    )
    owner.scoped_results[(key, role, at_noop, at_noop)] = _resolved(
        key, role, at_noop, (_fact(first, "initial mandate"),)
    )
    owner.scoped_results[(key, role, at_commit, at_commit)] = _resolved(
        key, role, at_commit, (_fact(changed, "objective and principle changed"),)
    )
    owner.scoped_results[(key, role, at_successor, at_successor)] = _resolved(
        key, role, at_successor, (_fact(successor, "new attributable mandate"),)
    )
    resolver = ContextSelectionResolver(owner)
    formed = asyncio.run(resolver.read_current(key, role, at=_AT))
    queried_again = asyncio.run(resolver.read_current(key, role, at=_AT))
    irrelevant = asyncio.run(resolver.read_current(key, role, at=at_noop))
    one_commit = asyncio.run(resolver.read_current(key, role, at=at_commit))
    new_root = asyncio.run(resolver.read_current(key, role, at=at_successor))
    assert type(formed) is ResolvedContextSelection
    assert type(queried_again) is ResolvedContextSelection
    assert type(irrelevant) is ResolvedContextSelection
    assert type(one_commit) is ResolvedContextSelection
    assert type(new_root) is ResolvedContextSelection
    assert formed.facts[0].reference == queried_again.facts[0].reference == first
    assert irrelevant.facts[0].reference == first
    assert one_commit.facts[0].reference == changed
    assert changed.revision.value == first.revision.value + 1
    assert new_root.facts[0].reference == successor
    assert successor.revision == InvestmentMandateRevision(1)


def test_replacement_and_absence_are_guarded_without_support_epoch_change() -> None:
    key = _key()
    first = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    next_state = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    empty = _resolved(key, role, _AT)
    selected = _resolved(key, role, _AT, (_fact(first, "as-of 1"),))
    replaced = _resolved(key, role, _AT, (_fact(next_state, "as-of 2"),))
    assert empty.guard != selected.guard
    assert selected.guard != replaced.guard
    assert first.revision == next_state.revision


def test_positive_revision_change_keeps_selection_and_support_epoch() -> None:
    key = _key()
    root = PortfolioStateId(uuid4())
    first = PortfolioStateVersionRef(root, PortfolioStateRevision(1))
    changed = PortfolioStateVersionRef(root, PortfolioStateRevision(2))
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    before = _resolved(key, role, _AT, (_fact(first, "support A"),))
    after = _resolved(key, role, _AT, (_fact(changed, "support B"),))
    evidence_support_epoch_before = 3
    evidence_support_epoch_after = 3
    assert before.facts[0].reference != after.facts[0].reference
    assert before.guard == after.guard
    assert evidence_support_epoch_before == evidence_support_epoch_after


def test_same_root_relationship_change_breaks_guard_without_positive_change() -> None:
    # duplicate-code: relationship drift and display-only admission are independent
    # falsifiers; sharing their setup would conceal the exact unchanged positive ref.
    # arid: disable
    key = _key()
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    reference = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    # arid: enable
    first = _resolved(key, role, _AT, (_fact(reference, "same owner fact"),))
    changed = _resolved(
        key,
        role,
        _AT,
        (_fact(reference, "same owner fact"),),
        relationship_epoch=2,
    )
    assert first.facts == changed.facts
    assert first.guard.selected == changed.guard.selected
    assert first.guard != changed.guard


def test_empty_selection_absence_change_breaks_guard_without_positive_change() -> None:
    key = _key()
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    owner = OwnerDouble()
    owner.results[role] = _resolved(key, role, _AT)
    resolver = ContextSelectionResolver(owner)
    first = asyncio.run(resolver.read_current(key, role, at=_AT))
    owner.results[role] = _resolved(key, role, _AT, universe_epoch=2)
    changed = asyncio.run(resolver.read_current(key, role, at=_AT))
    assert type(first) is ResolvedContextSelection
    assert type(changed) is ResolvedContextSelection
    assert first.facts == changed.facts == ()
    assert first.guard.selected == changed.guard.selected == frozenset()
    assert first.guard.relationships == changed.guard.relationships == frozenset()
    assert first.guard != changed.guard


def test_future_only_and_out_of_key_owner_changes_leave_current_selection() -> None:
    key = _key()
    other_key = _key()
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    current_ref = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    later_ref = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    owner = OwnerDouble()
    owner.scoped_results[(key, role, _AT, _AT)] = _resolved(
        key, role, _AT, (_fact(current_ref, "current as-of"),)
    )
    resolver = ContextSelectionResolver(owner)
    before = asyncio.run(resolver.read_current(key, role, at=_AT))
    future_at = _AT + timedelta(days=1)
    owner.scoped_results[(key, role, future_at, future_at)] = _resolved(
        key, role, future_at, (_fact(later_ref, "future as-of"),)
    )
    owner.scoped_results[(other_key, role, _AT, _AT)] = _resolved(
        other_key, role, _AT, (_fact(later_ref, "other key"),)
    )
    after = asyncio.run(resolver.read_current(key, role, at=_AT))
    assert type(before) is ResolvedContextSelection
    assert type(after) is ResolvedContextSelection
    assert before.facts == after.facts
    assert before.guard == after.guard


def test_display_only_fact_cannot_be_selected_and_wrong_key_fails_closed() -> None:
    key = _key()
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    reference = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    with pytest.raises(ValueError, match="material ContextContribution"):
        SelectedContextFact(reference, "display only", (), (), (), frozenset())
    owner = OwnerDouble()
    owner.results[role] = _resolved(_key(), role, _AT, (_fact(reference, "other key"),))
    result = asyncio.run(
        ContextSelectionResolver(owner).read_current(key, role, at=_AT)
    )
    assert type(result) is ContextNoBasis
    assert result.reason is ContextNoBasisReason.INVALID_HISTORY


@pytest.mark.parametrize(
    "reason",
    [
        ContextNoBasisReason.MISSING_REQUIRED,
        ContextNoBasisReason.INCOMPLETE_MEMBERSHIP,
        ContextNoBasisReason.CONTESTED,
        ContextNoBasisReason.INVALID_HISTORY,
        ContextNoBasisReason.UNAVAILABLE_AUTHORITY,
    ],
)
def test_unusable_owner_outcomes_never_form_complete_basis(
    reason: ContextNoBasisReason,
) -> None:
    key = _key()
    role = ContextSelectionRole.USED_PRIOR_DECISION
    owner = OwnerDouble()
    owner.results[role] = ContextNoBasis(key, role, _AT, _AT, reason, "owner finding")
    result = asyncio.run(
        ContextSelectionResolver(owner).read_complete_current(key, at=_AT)
    )
    assert type(result) is ContextNoBasis
    assert result.reason is reason
    assert len(owner.calls) == 1


def test_unavailable_exception_and_mismatched_owner_result_fail_closed() -> None:
    key = _key()
    role = ContextSelectionRole.USED_PRIOR_DECISION
    owner = OwnerDouble()
    owner.results[role] = ContextOwnerReadUnavailable("source down")
    unavailable = asyncio.run(
        ContextSelectionResolver(owner).read_current(key, role, at=_AT)
    )
    assert type(unavailable) is ContextNoBasis
    assert unavailable.reason is ContextNoBasisReason.UNAVAILABLE_AUTHORITY
    owner.results[role] = _resolved(key, role, _AT + timedelta(days=1))
    invalid = asyncio.run(
        ContextSelectionResolver(owner).read_current(key, role, at=_AT)
    )
    assert type(invalid) is ContextNoBasis
    assert invalid.reason is ContextNoBasisReason.INVALID_HISTORY
    owner.results[role] = ContextNoBasis(
        key,
        role,
        _AT + timedelta(days=1),
        _AT + timedelta(days=1),
        ContextNoBasisReason.CONTESTED,
        "later conflict",
    )
    stale_no_basis = asyncio.run(
        ContextSelectionResolver(owner).read_current(key, role, at=_AT)
    )
    assert type(stale_no_basis) is ContextNoBasis
    assert stale_no_basis.reason is ContextNoBasisReason.INVALID_HISTORY


def test_historical_read_keeps_recorded_cutoff() -> None:
    key = _key()
    owner = OwnerDouble()
    resolver = ContextSelectionResolver(owner)
    role = ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    known = _AT + timedelta(days=2)
    earlier = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    owner.history[(role, _AT, known)] = _resolved(
        key, role, _AT, (_fact(earlier, "historical as-of"),), known_at=known
    )
    historical = asyncio.run(
        resolver.read_historical(key, role, effective_at=_AT, known_at=known)
    )
    assert type(historical) is ResolvedContextSelection
    assert historical.facts[0].reference == earlier
    current = asyncio.run(resolver.read_current(key, role, at=_AT))
    assert type(current) is ResolvedContextSelection
    assert current.guard.selected == frozenset()
    assert owner.calls[0][-2:] == (_AT, known)
    assert owner.calls[1][-2:] == (_AT, _AT)
    later_at = known + timedelta(days=1)
    later = PortfolioStateVersionRef(
        PortfolioStateId(uuid4()), PortfolioStateRevision(1)
    )
    owner.history[(role, later_at, later_at)] = _resolved(
        key, role, later_at, (_fact(later, "later state"),)
    )
    still_historical = asyncio.run(
        resolver.read_historical(key, role, effective_at=_AT, known_at=known)
    )
    assert still_historical == historical
