"""Portfolio owner versions and selection guards across exact Evidence keys."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from polaris.application.evidence.context_versions import (
    ContextContribution,
    ContextNoBasis,
    ContextNoBasisReason,
    ResolvedContextSelection,
)
from polaris.application.evidence.owner_meaning import CanonicalContextMeaning
from polaris.application.portfolio_context import (
    InvalidPortfolioContextHistory,
    PortfolioContextCommit,
    PortfolioContextFactAct,
    PortfolioContextHistory,
    PortfolioContextMeaningReader,
    PortfolioContextOwner,
    PortfolioContextSelectionAct,
)
from polaris.domain.configuration import InvestmentHorizon
from polaris.domain.decisions.facts import InvestmentDecisionId
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextRootRef,
    ContextSelectionRole,
    InvestmentMandateId,
    InvestmentMandateRevision,
    InvestmentMandateVersionRef,
    InvestmentStrategyId,
    InvestmentStrategyRevision,
    InvestmentStrategyVersionRef,
    PortfolioBoundaryId,
    PortfolioBoundaryRevision,
    PortfolioBoundaryVersionRef,
    PortfolioStateRevision,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateId,
    ProjectedPortfolioStateRevision,
    ProjectedPortfolioStateVersionRef,
    context_root,
)
from polaris.domain.evidence.judgments import (
    EvidenceUse,
    InvestmentViewRef,
    JudgmentWideEvidenceScope,
)
from polaris.domain.portfolio import (
    FinancialInstrumentId,
    PortfolioId,
    PortfolioSource,
    PortfolioState,
    PortfolioStateId,
    RecordedPortfolioState,
)
from polaris.domain.portfolio_context import (
    ActualPortfolioStateMeaning,
    InvestmentMandateMeaning,
    InvestmentStrategyMeaning,
    MandateMember,
    MandateMemberKind,
    MandateMemberRef,
    PortfolioBoundaryMeaning,
    PortfolioContextMeaning,
    PortfolioContextVersionRef,
    ProjectedPortfolioStateMeaning,
)
from polaris.infrastructure.persistence.postgresql.portfolio_context_codec import (
    commit_from_payload,
    commit_payload,
)

AT = datetime(2026, 1, 1, tzinfo=UTC)
LATER = AT + timedelta(days=1)


# duplicate-code: this owner fixture is independent of Evidence scope proofs.
# arid: disable
def _key() -> BasisScopeKey:
    return BasisScopeKey(
        InvestmentDecisionId(uuid4()),
        InvestmentViewRef(uuid4()),
        JudgmentWideEvidenceScope(),
        EvidenceUse.JUDGMENT_BASIS,
    )


# arid: enable


def _state() -> RecordedPortfolioState:
    state = PortfolioState(
        PortfolioStateId(uuid4()),
        PortfolioId(uuid4()),
        AT,
        PortfolioSource("custodian", "snapshot-1", AT),
        "USD",
        Decimal("100000"),
        Decimal("20000"),
        FinancialInstrumentId(uuid4()),
        Decimal("100"),
        Decimal("80000"),
        Decimal("80000"),
        Decimal("0.8"),
        "Source position interpreted for the Decision",
    )
    return RecordedPortfolioState(state, AT)


def _families() -> tuple[
    tuple[ContextSelectionRole, PortfolioContextVersionRef, PortfolioContextMeaning],
    ...,
]:
    state = _state()
    portfolio = state.state.portfolio_id
    member = MandateMember(
        MandateMemberRef(MandateMemberKind.OBJECTIVE, uuid4()),
        "Preserve enough liquidity",
        AT,
        None,
    )
    principle = MandateMember(
        MandateMemberRef(MandateMemberKind.PRINCIPLE, uuid4()),
        "Respect the liquidity objective",
        AT,
        None,
        (member.reference,),
    )
    return (
        (
            ContextSelectionRole.PORTFOLIO_BOUNDARY,
            PortfolioBoundaryVersionRef(
                PortfolioBoundaryId(uuid4()), PortfolioBoundaryRevision(1)
            ),
            PortfolioBoundaryMeaning(
                portfolio, state.state.instrument_id, "one Portfolio and SPY"
            ),
        ),
        (
            ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
            PortfolioStateVersionRef(state.state.state_id, PortfolioStateRevision(1)),
            ActualPortfolioStateMeaning(state),
        ),
        (
            ContextSelectionRole.PROJECTED_PORTFOLIO_STATE,
            ProjectedPortfolioStateVersionRef(
                ProjectedPortfolioStateId(uuid4()), ProjectedPortfolioStateRevision(1)
            ),
            ProjectedPortfolioStateMeaning(
                portfolio,
                state.state.state_id,
                InvestmentHorizon("one quarter"),
                "flat market",
                Decimal("90000"),
                Decimal("10000"),
                "future returns remain unknown",
            ),
        ),
        (
            ContextSelectionRole.INVESTMENT_MANDATE,
            InvestmentMandateVersionRef(
                InvestmentMandateId(uuid4()), InvestmentMandateRevision(1)
            ),
            InvestmentMandateMeaning(portfolio, (member, principle)),
        ),
        (
            ContextSelectionRole.INVESTMENT_STRATEGY,
            InvestmentStrategyVersionRef(
                InvestmentStrategyId(uuid4()), InvestmentStrategyRevision(1)
            ),
            InvestmentStrategyMeaning(portfolio, "Maintain the SPY allocation"),
        ),
    )


def _fact(
    reference: PortfolioContextVersionRef,
    meaning: PortfolioContextMeaning,
    *,
    at: datetime = AT,
) -> PortfolioContextFactAct:
    return PortfolioContextFactAct(
        uuid4(),
        reference,
        meaning,
        at,
        at,
        "Portfolio owner fact and source provenance",
        frozenset({ContextContribution.APPLICABILITY, ContextContribution.SUPPORT}),
    )


def _selection(
    key: BasisScopeKey,
    role: ContextSelectionRole,
    roots: frozenset[ContextRootRef],
    *,
    effective_at: datetime = AT,
    known_at: datetime = AT,
    basis: str = "materially used for this exact basis",
) -> PortfolioContextSelectionAct:
    return PortfolioContextSelectionAct(
        uuid4(), key, role, roots, effective_at, known_at, basis
    )


class MemoryStore:
    def __init__(self) -> None:
        self.history = PortfolioContextHistory()
        self.states: dict[PortfolioStateId, RecordedPortfolioState] = {}

    async def get(self, state_id: PortfolioStateId) -> RecordedPortfolioState | None:
        return self.states.get(state_id)

    async def load(self) -> PortfolioContextHistory:
        return self.history

    async def append(
        self, commit: PortfolioContextCommit, *, expected_last_commit: UUID | None
    ) -> PortfolioContextHistory:
        actual = self.history.commits[-1].commit_id if self.history.commits else None
        if actual != expected_last_commit:
            raise AssertionError("concurrent append")
        self.history = self.history.append(commit)
        return self.history


def _record(
    owner: PortfolioContextOwner,
    at: datetime,
    facts: tuple[PortfolioContextFactAct, ...] = (),
    selections: tuple[PortfolioContextSelectionAct, ...] = (),
) -> PortfolioContextHistory:
    return asyncio.run(
        owner.commit(PortfolioContextCommit(uuid4(), at, facts, selections))
    )


def _selected_family_acts(
    key: BasisScopeKey,
    families: tuple[
        tuple[
            ContextSelectionRole,
            PortfolioContextVersionRef,
            PortfolioContextMeaning,
        ],
        ...,
    ],
) -> tuple[
    tuple[PortfolioContextFactAct, ...], tuple[PortfolioContextSelectionAct, ...]
]:
    facts = tuple(_fact(reference, meaning) for _, reference, meaning in families)
    selections = tuple(
        _selection(key, role, frozenset({context_root(reference)}))
        for role, reference, _ in families
    )
    return facts, selections


def _mandate_family() -> tuple[InvestmentMandateVersionRef, InvestmentMandateMeaning]:
    _, reference, meaning = _families()[3]
    assert isinstance(reference, InvestmentMandateVersionRef)
    assert isinstance(meaning, InvestmentMandateMeaning)
    return reference, meaning


def _select_initial(
    owner: PortfolioContextOwner,
    key: BasisScopeKey,
    role: ContextSelectionRole,
    reference: PortfolioContextVersionRef,
    meaning: PortfolioContextMeaning,
) -> None:
    _record(
        owner,
        AT,
        (_fact(reference, meaning),),
        (_selection(key, role, frozenset({context_root(reference)})),),
    )


def test_each_portfolio_family_is_typed_and_selected_with_complete_guard() -> None:
    key = _key()
    families = _families()
    facts, selections = _selected_family_acts(key, families)
    store = MemoryStore()
    for _, _, meaning in families:
        if isinstance(meaning, ActualPortfolioStateMeaning):
            store.states[meaning.recorded.state.state_id] = meaning.recorded
    owner = PortfolioContextOwner(store, store)
    _record(owner, AT, facts, selections)
    for role, reference, meaning in families:
        result = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
        assert type(result) is ResolvedContextSelection
        assert result.facts[0].reference == reference
        assert result.facts[0].fact == meaning
        assert result.guard.selected == frozenset({context_root(reference)})
        assert result.guard.relationships
        assert result.guard.universe.role is role
        if role is ContextSelectionRole.ACTUAL_PORTFOLIO_STATE:
            actual = result.facts[0].fact
            assert type(actual) is ActualPortfolioStateMeaning
            assert actual.recorded.state.source.system == "custodian"
            assert actual.recorded.state.as_of == AT
        if role is ContextSelectionRole.INVESTMENT_MANDATE:
            mandate = result.facts[0].fact
            assert type(mandate) is InvestmentMandateMeaning
            assert mandate.members[1].depends_on == (mandate.members[0].reference,)


def test_mandate_member_correction_advances_once_and_history_remains_readable() -> None:
    key = _key()
    role = ContextSelectionRole.INVESTMENT_MANDATE
    reference, meaning = _mandate_family()
    root = reference.root
    store = MemoryStore()
    owner = PortfolioContextOwner(store)
    _select_initial(owner, key, role, reference, meaning)
    corrected_member = replace(
        meaning.members[0], content="Maintain a larger cash buffer"
    )
    corrected = replace(meaning, members=(corrected_member, meaning.members[1]))
    next_ref = InvestmentMandateVersionRef(root, InvestmentMandateRevision(2))
    next_fact = _fact(next_ref, corrected, at=LATER)
    _record(owner, LATER, (next_fact,))
    historical = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
    current = asyncio.run(owner.read_at(key, role, effective_at=LATER, known_at=LATER))
    assert type(historical) is ResolvedContextSelection
    assert type(current) is ResolvedContextSelection
    assert historical.facts[0].reference == reference
    assert current.facts[0].reference == next_ref
    assert historical.guard == current.guard
    assert current.facts[0].fact == corrected
    with pytest.raises(InvalidPortfolioContextHistory):
        store.history.append(
            PortfolioContextCommit(
                uuid4(),
                LATER + timedelta(days=1),
                (_fact(next_ref, corrected, at=LATER + timedelta(days=1)),),
                (),
            )
        )


def test_future_selection_stays_out_of_current_basis_until_effective() -> None:
    key = _key()
    role, first_ref, first_meaning = _families()[1]
    assert isinstance(first_ref, PortfolioStateVersionRef)
    assert isinstance(first_meaning, ActualPortfolioStateMeaning)
    first_root = first_ref.root
    next_state = replace(
        first_meaning.recorded.state,
        state_id=PortfolioStateId(uuid4()),
        as_of=LATER,
        source=PortfolioSource("custodian", "snapshot-2", LATER),
    )
    next_ref = PortfolioStateVersionRef(next_state.state_id, PortfolioStateRevision(1))
    next_meaning = ActualPortfolioStateMeaning(
        RecordedPortfolioState(next_state, LATER)
    )
    store = MemoryStore()
    store.states[first_meaning.recorded.state.state_id] = first_meaning.recorded
    store.states[next_state.state_id] = next_meaning.recorded
    owner = PortfolioContextOwner(store, store)
    _select_initial(owner, key, role, first_ref, first_meaning)
    scheduled_at = AT + timedelta(hours=1)
    # duplicate-code: future activation and current change are separate proofs.
    # arid: disable
    future_selection = _selection(
        key,
        role,
        frozenset({next_ref.root}),
        effective_at=LATER,
        known_at=scheduled_at,
    )
    # arid: enable
    _record(owner, scheduled_at, selections=(future_selection,))
    _record(owner, LATER, (_fact(next_ref, next_meaning, at=LATER),))
    before = asyncio.run(
        owner.read_at(
            key,
            role,
            effective_at=scheduled_at,
            known_at=scheduled_at,
        )
    )
    after = asyncio.run(
        owner.read_at(
            key,
            role,
            effective_at=LATER,
            known_at=LATER,
        )
    )
    assert type(before) is ResolvedContextSelection
    assert type(after) is ResolvedContextSelection
    assert before.facts[0].reference == first_ref
    assert after.facts[0].reference == next_ref
    assert before.guard != after.guard
    assert before.guard.selected == frozenset({first_root})
    assert after.guard.selected == frozenset({next_ref.root})


def test_selected_missing_and_contested_facts_return_distinct_no_basis() -> None:
    key = _key()
    role, reference, meaning = _families()[4]
    store = MemoryStore()
    owner = PortfolioContextOwner(store)
    _record(
        owner,
        AT,
        selections=(
            _selection(
                key,
                role,
                frozenset({context_root(reference)}),
                effective_at=LATER,
            ),
        ),
    )
    missing = asyncio.run(owner.read_at(key, role, effective_at=LATER, known_at=LATER))
    assert type(missing) is ContextNoBasis
    assert missing.reason is ContextNoBasisReason.INCOMPLETE_MEMBERSHIP
    store.history = PortfolioContextHistory()
    contested = replace(_fact(reference, meaning), contested=True)
    _record(
        owner,
        AT,
        (contested,),
        (_selection(key, role, frozenset({context_root(reference)})),),
    )
    result = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
    assert type(result) is ContextNoBasis
    assert result.reason is ContextNoBasisReason.CONTESTED


def test_closed_codec_round_trip_preserves_typed_history() -> None:
    key = _key()
    families = _families()
    facts, selections = _selected_family_acts(key, families)
    commit = PortfolioContextCommit(uuid4(), AT, facts, selections)
    assert commit_from_payload(commit_payload(commit)) == commit


def test_mandate_temporal_applicability_has_same_version_and_owner_cause() -> None:
    key = _key()
    role = ContextSelectionRole.INVESTMENT_MANDATE
    reference, meaning = _mandate_family()
    later_member = MandateMember(
        MandateMemberRef(MandateMemberKind.OBJECTIVE, uuid4()),
        "Increase long-horizon growth exposure",
        LATER,
        None,
    )
    full = replace(meaning, members=(*meaning.members, later_member))
    store = MemoryStore()
    owner = PortfolioContextOwner(store)
    _select_initial(owner, key, role, reference, full)
    before = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
    after = asyncio.run(owner.read_at(key, role, effective_at=LATER, known_at=LATER))
    assert type(before) is ResolvedContextSelection
    assert type(after) is ResolvedContextSelection
    assert before.facts[0].reference == after.facts[0].reference == reference
    assert before.guard == after.guard
    assert before.facts[0].fact != after.facts[0].fact
    assert type(after.facts[0].fact) is InvestmentMandateMeaning
    assert later_member in after.facts[0].fact.members
    meaning_reader = PortfolioContextMeaningReader(store)
    old_subject = CanonicalContextMeaning(role, reference, before.guard)
    new_subject = CanonicalContextMeaning(role, reference, after.guard)
    old_witness = asyncio.run(
        meaning_reader.read_at(
            key, old_subject, effective_at=AT, known_at=AT, read_at=AT
        )
    )
    new_witness = asyncio.run(
        meaning_reader.read_at(
            key, new_subject, effective_at=LATER, known_at=LATER, read_at=LATER
        )
    )
    assert old_witness.meaning != new_witness.meaning
    assert old_witness.cause.fact_ancestry == new_witness.cause.fact_ancestry
    assert (
        asyncio.run(meaning_reader.verify_cause(old_witness, validation_at=LATER)).value
        == "valid"
    )
    assert (
        asyncio.run(meaning_reader.verify_cause(new_witness, validation_at=AT)).value
        == "invalid_history"
    )


def test_actual_state_context_requires_the_canonical_state_fact() -> None:
    role, reference, meaning = _families()[1]
    assert role is ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    assert isinstance(reference, PortfolioStateVersionRef)
    assert isinstance(meaning, ActualPortfolioStateMeaning)
    key = _key()
    commit = PortfolioContextCommit(
        uuid4(),
        AT,
        (_fact(reference, meaning),),
        (_selection(key, role, frozenset({reference.root})),),
    )
    store = MemoryStore()
    owner = PortfolioContextOwner(store, store)
    with pytest.raises(ValueError, match="canonical State"):
        asyncio.run(owner.commit(commit))
    store.states[reference.root] = meaning.recorded
    asyncio.run(owner.commit(commit))
    store.states.pop(reference.root)
    result = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
    assert type(result) is ContextNoBasis
    assert result.reason is ContextNoBasisReason.INVALID_HISTORY


def test_current_selection_change_updates_exact_guard_without_revising_old_root() -> (
    None
):
    key = _key()
    role, first_ref, first_meaning = _families()[0]
    assert isinstance(first_ref, PortfolioBoundaryVersionRef)
    assert isinstance(first_meaning, PortfolioBoundaryMeaning)
    next_ref = PortfolioBoundaryVersionRef(
        PortfolioBoundaryId(uuid4()), PortfolioBoundaryRevision(1)
    )
    next_meaning = replace(first_meaning, boundary="different selected boundary")
    store = MemoryStore()
    owner = PortfolioContextOwner(store)
    _select_initial(owner, key, role, first_ref, first_meaning)
    replacement = _selection(
        key,
        role,
        frozenset({next_ref.root}),
        effective_at=LATER,
        known_at=LATER,
    )
    _record(
        owner,
        LATER,
        (_fact(next_ref, next_meaning, at=LATER),),
        (replacement,),
    )
    old = asyncio.run(owner.read_at(key, role, effective_at=AT, known_at=AT))
    current = asyncio.run(owner.read_at(key, role, effective_at=LATER, known_at=LATER))
    assert type(old) is ResolvedContextSelection
    assert type(current) is ResolvedContextSelection
    assert old.guard != current.guard
    assert current.facts[0].reference == next_ref


def test_selecting_existing_root_for_another_key_preserves_first_key_basis() -> None:
    key_a = _key()
    key_b = _key()
    role, reference, meaning = _families()[0]
    assert isinstance(reference, PortfolioBoundaryVersionRef)
    store = MemoryStore()
    owner = PortfolioContextOwner(store)
    _select_initial(owner, key_a, role, reference, meaning)
    before = asyncio.run(owner.read_at(key_a, role, effective_at=AT, known_at=AT))
    assert type(before) is ResolvedContextSelection
    _record(
        owner,
        LATER,
        selections=(
            _selection(
                key_b,
                role,
                frozenset({reference.root}),
                effective_at=LATER,
                known_at=LATER,
            ),
        ),
    )
    after = asyncio.run(owner.read_at(key_a, role, effective_at=LATER, known_at=LATER))
    other = asyncio.run(owner.read_at(key_b, role, effective_at=LATER, known_at=LATER))
    assert type(after) is ResolvedContextSelection
    assert type(other) is ResolvedContextSelection
    assert after.facts[0].reference == before.facts[0].reference == reference
    assert after.guard == before.guard
    assert other.facts[0].reference == reference
    assert other.guard.key == key_b
