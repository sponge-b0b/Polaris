"""Portfolio owner facts participate in complete Evidence dependent commits."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from polaris.application.evidence.context_versions import ContextSelectionResolver
from polaris.application.evidence.current_basis import (
    BasisGuardRole,
    BasisPositiveRole,
    CurrentEvidenceBasis,
    CurrentEvidenceBasisQuery,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
)
from polaris.application.evidence.owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    OwnerCauseVerdict,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningResolver,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
)
from polaris.application.evidence.reconstruction import (
    StaleEvidenceBasis,
    StaleEvidenceBasisCategory,
)
from polaris.application.evidence.revalidation import (
    AtomicCurrentBasisRead,
    CurrentEvidenceBasisRevalidator,
)
from polaris.application.portfolio_context import (
    PORTFOLIO_CONTEXT_ROLES,
    PortfolioContextMeaningReader,
    PortfolioContextOwner,
)
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextSelectionRole,
    PortfolioStateRevision,
    PortfolioStateVersionRef,
)
from polaris.domain.portfolio import (
    PortfolioSource,
    PortfolioStateId,
    RecordedPortfolioState,
)
from polaris.domain.portfolio_context import (
    ActualPortfolioStateMeaning,
    InvestmentMandateMeaning,
    MandateMember,
    MandateMemberKind,
    MandateMemberRef,
    PortfolioContextMeaning,
    PortfolioContextVersionRef,
)
from tests.application.evidence.test_current_basis import (
    AT,
    _complete_current,
    _Contexts,
    _empty_query,
    _enroll_temporal_target,
    _MeaningOwner,
)
from tests.application.test_portfolio_context import (
    AT as PORTFOLIO_AT,
)
from tests.application.test_portfolio_context import (
    MemoryStore,
    _fact,
    _families,
    _record,
    _selected_family_acts,
    _selection,
)
from tests.domain.configuration.configuration_support import requirement_key

LATER = AT + timedelta(days=1)


class _PortfolioContexts:
    def __init__(self, owner: PortfolioContextOwner, others: _Contexts) -> None:
        self.owner = owner
        self.others = others

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> object:
        reader = self.owner if role in PORTFOLIO_CONTEXT_ROLES else self.others
        return await reader.read_at(
            key, role, effective_at=effective_at, known_at=known_at
        )


class _PortfolioMeanings:
    def __init__(
        self, portfolio: PortfolioContextMeaningReader, others: _MeaningOwner
    ) -> None:
        self.portfolio = portfolio
        self.others = others

    def _reader(
        self, subject: OwnerMeaningSubject
    ) -> PortfolioContextMeaningReader | _MeaningOwner:
        if isinstance(subject, (CanonicalContextMeaning, CanonicalContextAbsence)):
            if subject.role in PORTFOLIO_CONTEXT_ROLES:
                return self.portfolio
        return self.others

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> OwnerMeaningWitness | OwnerMeaningNoBasis:
        return await self._reader(subject).read_at(
            key,
            subject,
            effective_at=effective_at,
            known_at=known_at,
            read_at=read_at,
        )

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        return await self._reader(witness.subject).verify_cause(
            witness, validation_at=validation_at
        )


class _JudgmentTransaction:
    def __init__(self, boundary: _JudgmentBoundary) -> None:
        self.boundary = boundary
        self.pending: str | None = None

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead | None:
        if not self.boundary.available:
            return None
        return AtomicCurrentBasisRead(key, self.boundary.at, self.boundary.query)

    async def write(self) -> str:
        assert self.boundary.open
        self.pending = "dependent judgment"
        return self.pending


class _JudgmentBoundary:
    def __init__(
        self, query: CurrentEvidenceBasisQuery, at: datetime, *, available: bool = True
    ) -> None:
        self.query = query
        self.at = at
        self.available = available
        self.open = False
        self.committed: list[str] = []

    def transaction(
        self, key: BasisScopeKey
    ) -> AbstractAsyncContextManager[_JudgmentTransaction]:
        return self._transaction(key)

    @asynccontextmanager
    async def _transaction(
        self, key: BasisScopeKey
    ) -> AsyncIterator[_JudgmentTransaction]:
        assert not self.open
        self.open = True
        transaction = _JudgmentTransaction(self)
        try:
            yield transaction
            if transaction.pending is not None:
                self.committed.append(transaction.pending)
        finally:
            self.open = False


def _owner_basis() -> tuple[
    CurrentEvidenceBasisQuery, BasisScopeKey, Any, MemoryStore, PortfolioContextOwner
]:
    query, key, target, others, *_ = _empty_query(requirement_key())
    _enroll_temporal_target(query, target)
    families = _families()
    store, owner = _record_selected_families(key, families)
    other_meanings = query._context_meaning._owner
    query._contexts = ContextSelectionResolver(_PortfolioContexts(owner, others))
    query._context_meaning = OwnerMeaningResolver(
        _PortfolioMeanings(PortfolioContextMeaningReader(store, store), other_meanings)
    )
    return query, key, families, store, owner


def _commit(
    prior: CurrentEvidenceBasis,
    query: CurrentEvidenceBasisQuery,
    *,
    available: bool = True,
) -> tuple[object, _JudgmentBoundary]:
    boundary = _JudgmentBoundary(query, LATER, available=available)
    result = asyncio.run(CurrentEvidenceBasisRevalidator().commit(prior, boundary))
    return result, boundary


def _record_selected_families(
    key: BasisScopeKey,
    families: tuple[
        tuple[
            ContextSelectionRole, PortfolioContextVersionRef, PortfolioContextMeaning
        ],
        ...,
    ],
) -> tuple[MemoryStore, PortfolioContextOwner]:
    # duplicate-code: this Evidence commit fixture must stay independent of the
    # Portfolio owner proof; sharing setup would couple their falsifiers.
    # arid: disable
    store = MemoryStore()
    for _, _, meaning in families:
        if isinstance(meaning, ActualPortfolioStateMeaning):
            store.states[meaning.recorded.state.state_id] = meaning.recorded
    owner = PortfolioContextOwner(store, store)
    # arid: enable
    facts, selections = _selected_family_acts(key, families)
    _record(owner, PORTFOLIO_AT, facts, selections)
    return store, owner


def test_portfolio_owner_context_allows_unchanged_basis_to_commit() -> None:
    query, key, _, _, _ = _owner_basis()
    prior = _complete_current(query, key)

    result, boundary = _commit(prior, query)

    assert result == "dependent judgment"
    assert boundary.committed == ["dependent judgment"]
    assert not boundary.open


def test_portfolio_mandate_revision_stales_without_evidence_epoch_change() -> None:
    query, key, families, _, owner = _owner_basis()
    prior = _complete_current(query, key)
    role, reference, meaning = families[3]
    assert isinstance(meaning, InvestmentMandateMeaning)
    revised = replace(
        meaning,
        members=(
            replace(meaning.members[0], content="Keep a larger buffer"),
            *meaning.members[1:],
        ),
    )
    next_ref = type(reference)(reference.root, type(reference.revision)(2))
    _record(owner, LATER, (_fact(next_ref, revised, at=LATER),))

    result, boundary = _commit(prior, query)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
    assert any(
        item.role is BasisPositiveRole.CONTEXT
        and item.prior == reference
        and item.fresh == next_ref
        for item in result.changed_positive_references
    )
    assert prior.support_version.value == 1
    assert boundary.committed == []


def test_fresh_actual_state_root_breaks_selection_guard_without_write() -> None:
    query, key, families, store, owner = _owner_basis()
    prior = _complete_current(query, key)
    role, reference, meaning = families[1]
    assert role is ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
    assert isinstance(meaning, ActualPortfolioStateMeaning)
    state = replace(
        meaning.recorded.state,
        state_id=PortfolioStateId(uuid4()),
        as_of=LATER,
        source=PortfolioSource("custodian", "new snapshot", LATER),
    )
    recorded = RecordedPortfolioState(state, LATER)
    store.states[state.state_id] = recorded
    new_ref = PortfolioStateVersionRef(state.state_id, PortfolioStateRevision(1))
    _record(
        owner,
        LATER,
        (_fact(new_ref, ActualPortfolioStateMeaning(recorded), at=LATER),),
        (
            _selection(
                key,
                role,
                frozenset({state.state_id}),
                effective_at=LATER,
                known_at=LATER,
            ),
        ),
    )

    result, boundary = _commit(prior, query)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {
        StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED,
        StaleEvidenceBasisCategory.NEGATIVE_PREDICATE_BROKEN,
    }
    assert any(
        item.role is BasisGuardRole.CONTEXT_SELECTION for item in result.broken_guards
    )
    assert reference in prior.context.positive_references
    assert new_ref in {item.fresh for item in result.changed_positive_references}
    assert boundary.committed == []


def test_lawful_same_version_portfolio_meaning_change_stales_at_commit() -> None:
    query, key, families, store, owner = _owner_basis()
    role, reference, meaning = families[3]
    assert isinstance(meaning, InvestmentMandateMeaning)
    future_member = MandateMember(
        MandateMemberRef(MandateMemberKind.OBJECTIVE, uuid4()),
        "Increase growth exposure later",
        LATER,
        None,
    )
    initial = replace(meaning, members=(*meaning.members, future_member))
    first = store.history.commits[0]
    facts = tuple(
        replace(fact, meaning=initial) if fact.reference == reference else fact
        for fact in first.facts
    )
    store.history = type(store.history)((replace(first, facts=facts),))
    prior = _complete_current(query, key)

    result, boundary = _commit(prior, query)

    assert isinstance(result, StaleEvidenceBasis)
    assert result.categories == {StaleEvidenceBasisCategory.EVIDENCE_SUPPORT_CHANGED}
    assert result.changed_positive_references == ()
    assert any(
        item.role is BasisPositiveRole.CONTEXT
        and item.prior.subject == item.fresh.subject
        and item.fresh.cause.complete
        for item in result.changed_owner_meanings
    )
    assert boundary.committed == []


def test_invalid_history_and_missing_participation_have_distinct_no_basis() -> None:
    query, key, families, store, _ = _owner_basis()
    prior = _complete_current(query, key)
    _, _, meaning = families[1]
    assert isinstance(meaning, ActualPortfolioStateMeaning)
    store.states.pop(meaning.recorded.state.state_id)

    invalid, invalid_boundary = _commit(prior, query)
    unavailable, unavailable_boundary = _commit(prior, query, available=False)

    assert isinstance(invalid, CurrentEvidenceNoBasis)
    assert invalid.reason is CurrentNoBasisReason.INVALID_HISTORY
    assert isinstance(unavailable, CurrentEvidenceNoBasis)
    assert unavailable.reason is CurrentNoBasisReason.UNAVAILABLE
    assert invalid_boundary.committed == unavailable_boundary.committed == []
