"""Portfolio-owned context version history and exact Evidence selection reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Protocol
from uuid import UUID

from polaris.application.evidence.context_versions import (
    ContextContribution,
    ContextNoBasis,
    ContextNoBasisReason,
    ResolvedContextSelection,
    SelectedContextFact,
    validate_context_contributions,
)
from polaris.application.evidence.owner_meaning import (
    CanonicalContextAbsence,
    CanonicalContextMeaning,
    OwnerCauseVerdict,
    OwnerHistoryRecord,
    OwnerMeaningCause,
    OwnerMeaningNoBasis,
    OwnerMeaningNoBasisReason,
    OwnerMeaningSubject,
    OwnerMeaningWitness,
)
from polaris.application.portfolio import PortfolioStateStoreFailure
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    ContextRootRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    InvestmentMandateId,
    InvestmentMandateVersionRef,
    InvestmentStrategyId,
    InvestmentStrategyVersionRef,
    PortfolioBoundaryId,
    PortfolioBoundaryVersionRef,
    PortfolioStateVersionRef,
    ProjectedPortfolioStateId,
    ProjectedPortfolioStateVersionRef,
    context_root,
)
from polaris.domain.portfolio import PortfolioStateId, RecordedPortfolioState
from polaris.domain.portfolio_context import (
    ActualPortfolioStateMeaning,
    InvestmentMandateMeaning,
    PortfolioContextMeaning,
    PortfolioContextVersionRef,
    validate_portfolio_context_meaning,
)

PORTFOLIO_CONTEXT_ROLES = frozenset(
    {
        ContextSelectionRole.PORTFOLIO_BOUNDARY,
        ContextSelectionRole.ACTUAL_PORTFOLIO_STATE,
        ContextSelectionRole.PROJECTED_PORTFOLIO_STATE,
        ContextSelectionRole.INVESTMENT_MANDATE,
        ContextSelectionRole.INVESTMENT_STRATEGY,
    }
)

_REFERENCE_BY_ROLE = {
    ContextSelectionRole.PORTFOLIO_BOUNDARY: PortfolioBoundaryVersionRef,
    ContextSelectionRole.ACTUAL_PORTFOLIO_STATE: PortfolioStateVersionRef,
    ContextSelectionRole.PROJECTED_PORTFOLIO_STATE: ProjectedPortfolioStateVersionRef,
    ContextSelectionRole.INVESTMENT_MANDATE: InvestmentMandateVersionRef,
    ContextSelectionRole.INVESTMENT_STRATEGY: InvestmentStrategyVersionRef,
}
_ROOT_BY_ROLE = {
    ContextSelectionRole.PORTFOLIO_BOUNDARY: PortfolioBoundaryId,
    ContextSelectionRole.ACTUAL_PORTFOLIO_STATE: PortfolioStateId,
    ContextSelectionRole.PROJECTED_PORTFOLIO_STATE: ProjectedPortfolioStateId,
    ContextSelectionRole.INVESTMENT_MANDATE: InvestmentMandateId,
    ContextSelectionRole.INVESTMENT_STRATEGY: InvestmentStrategyId,
}


def _aware(value: datetime, name: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True, slots=True)
class PortfolioContextFactAct:
    """One immutable owner commit of a root's interpreted meaning."""

    act_id: UUID
    reference: PortfolioContextVersionRef
    meaning: PortfolioContextMeaning
    effective_at: datetime
    known_at: datetime
    basis: str
    contributions: frozenset[ContextContribution]
    contested: bool = False

    def __post_init__(self) -> None:
        if type(self.act_id) is not UUID or self.act_id.version != 4:
            raise ValueError("act_id must be UUIDv4")
        validate_portfolio_context_meaning(self.reference, self.meaning)
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")
        if self.effective_at > self.known_at:
            raise ValueError("same-root fact correction cannot be future-effective")
        if isinstance(self.meaning, ActualPortfolioStateMeaning) and (
            self.meaning.recorded.known_at > self.known_at
            or self.meaning.recorded.state.as_of > self.effective_at
        ):
            raise ValueError("actual State context cannot precede its canonical fact")
        if type(self.basis) is not str or not self.basis.strip():
            raise ValueError("basis must be nonempty")
        validate_context_contributions(self.contributions)
        if type(self.contested) is not bool:
            raise TypeError("contested must be bool")


@dataclass(frozen=True, slots=True)
class PortfolioContextSelectionAct:
    """A complete owner selection for one exact Evidence key and context role."""

    act_id: UUID
    key: BasisScopeKey
    role: ContextSelectionRole
    selected: frozenset[ContextRootRef]
    effective_at: datetime
    known_at: datetime
    relationship_basis: str

    def __post_init__(self) -> None:
        if type(self.act_id) is not UUID or self.act_id.version != 4:
            raise ValueError("act_id must be UUIDv4")
        if (
            type(self.key) is not BasisScopeKey
            or self.role not in PORTFOLIO_CONTEXT_ROLES
        ):
            raise TypeError("selection needs a Portfolio context role and exact key")
        if type(self.selected) is not frozenset:
            raise TypeError("selected must be a frozenset")
        expected = _ROOT_BY_ROLE[self.role]
        if any(type(root) is not expected for root in self.selected):
            raise TypeError("selected roots must match the typed Portfolio role")
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")
        if (
            type(self.relationship_basis) is not str
            or not self.relationship_basis.strip()
        ):
            raise ValueError("relationship_basis must be nonempty")


@dataclass(frozen=True, slots=True)
class PortfolioContextCommit:
    """One atomic owner act, possibly changing facts and exact selections."""

    commit_id: UUID
    known_at: datetime
    facts: tuple[PortfolioContextFactAct, ...]
    selections: tuple[PortfolioContextSelectionAct, ...]

    def __post_init__(self) -> None:
        if type(self.commit_id) is not UUID or self.commit_id.version != 4:
            raise ValueError("commit_id must be UUIDv4")
        _aware(self.known_at, "known_at")
        if type(self.facts) is not tuple or any(
            type(item) is not PortfolioContextFactAct for item in self.facts
        ):
            raise TypeError("facts must contain PortfolioContextFactAct")
        if type(self.selections) is not tuple or any(
            type(item) is not PortfolioContextSelectionAct for item in self.selections
        ):
            raise TypeError("selections must contain PortfolioContextSelectionAct")
        if not self.facts and not self.selections:
            raise ValueError("commit must change a Portfolio context fact or selection")
        if any(item.known_at != self.known_at for item in self.facts) or any(
            item.known_at != self.known_at for item in self.selections
        ):
            raise ValueError("all owner acts must share the commit knowledge boundary")
        if len({context_root(item.reference) for item in self.facts}) != len(
            self.facts
        ):
            raise ValueError("one owner commit may advance a root only once")
        if len({(item.key, item.role) for item in self.selections}) != len(
            self.selections
        ):
            raise ValueError("one owner commit may select a role/key only once")


class InvalidPortfolioContextHistory(ValueError):
    """Owner history contradicts its typed revisions or selection acts."""


@dataclass(frozen=True, slots=True)
class PortfolioContextHistory:
    commits: tuple[PortfolioContextCommit, ...] = ()

    def __post_init__(self) -> None:
        if type(self.commits) is not tuple:
            raise TypeError("commits must be a tuple")
        seen_acts: set[UUID] = set()
        latest: dict[ContextRootRef, PortfolioContextFactAct] = {}
        current_selections: dict[
            tuple[BasisScopeKey, ContextSelectionRole],
            list[PortfolioContextSelectionAct],
        ] = {}
        selection_times: set[tuple[BasisScopeKey, ContextSelectionRole, datetime]] = (
            set()
        )
        previous_known: datetime | None = None
        for commit in self.commits:
            if type(commit) is not PortfolioContextCommit:
                raise TypeError("commits must contain PortfolioContextCommit")
            if previous_known is not None and commit.known_at <= previous_known:
                raise InvalidPortfolioContextHistory("owner commits must be ordered")
            previous_known = commit.known_at
            if commit.commit_id in seen_acts:
                raise InvalidPortfolioContextHistory("duplicate owner commit")
            seen_acts.add(commit.commit_id)
            for fact in commit.facts:
                _validate_fact_act(fact, seen_acts, latest)
            for selection in commit.selections:
                _validate_selection_act(
                    selection,
                    seen_acts,
                    selection_times,
                    current_selections,
                )

    def append(self, commit: PortfolioContextCommit) -> PortfolioContextHistory:
        return PortfolioContextHistory((*self.commits, commit))


def _validate_fact_act(
    fact: PortfolioContextFactAct,
    seen_acts: set[UUID],
    latest: dict[ContextRootRef, PortfolioContextFactAct],
) -> None:
    if fact.act_id in seen_acts:
        raise InvalidPortfolioContextHistory("duplicate owner act")
    seen_acts.add(fact.act_id)
    root = context_root(fact.reference)
    prior = latest.get(root)
    if prior is None:
        if fact.reference.revision.value != 1:
            raise InvalidPortfolioContextHistory("new root must start at 1")
    else:
        if type(prior.reference) is not type(fact.reference):
            raise InvalidPortfolioContextHistory("root changed family")
        if fact.reference.revision.value != prior.reference.revision.value + 1:
            raise InvalidPortfolioContextHistory("changed root must advance once")
        if (
            fact.meaning == prior.meaning
            and fact.basis == prior.basis
            and fact.contributions == prior.contributions
            and fact.contested == prior.contested
        ):
            raise InvalidPortfolioContextHistory("unchanged root cannot advance")
        if (
            isinstance(fact.meaning, ActualPortfolioStateMeaning)
            and isinstance(prior.meaning, ActualPortfolioStateMeaning)
            and fact.meaning.recorded.state.as_of != prior.meaning.recorded.state.as_of
        ):
            raise InvalidPortfolioContextHistory(
                "fresh as-of Portfolio State requires a new root"
            )
    latest[root] = fact


def _validate_selection_act(
    selection: PortfolioContextSelectionAct,
    seen_acts: set[UUID],
    selection_times: set[tuple[BasisScopeKey, ContextSelectionRole, datetime]],
    current_selections: dict[
        tuple[BasisScopeKey, ContextSelectionRole],
        list[PortfolioContextSelectionAct],
    ],
) -> None:
    if selection.act_id in seen_acts:
        raise InvalidPortfolioContextHistory("duplicate owner act")
    seen_acts.add(selection.act_id)
    identity = (selection.key, selection.role, selection.effective_at)
    if identity in selection_times:
        raise InvalidPortfolioContextHistory(
            "competing selection acts at one effective boundary"
        )
    selection_times.add(identity)
    scope = (selection.key, selection.role)
    prior_acts = current_selections.setdefault(scope, [])
    current_prior = max(
        (item for item in prior_acts if item.effective_at <= selection.known_at),
        key=lambda item: item.effective_at,
        default=None,
    )
    affects_current = selection.effective_at <= selection.known_at and (
        current_prior is None or selection.effective_at > current_prior.effective_at
    )
    if affects_current:
        old_roots = frozenset() if current_prior is None else current_prior.selected
        prior_basis = (
            None if current_prior is None else current_prior.relationship_basis
        )
        if (
            selection.selected == old_roots
            and selection.relationship_basis == prior_basis
        ):
            raise InvalidPortfolioContextHistory(
                "unchanged current selection cannot create a new guard"
            )
    prior_acts.append(selection)


@dataclass(frozen=True, slots=True)
class PortfolioContextRelationship:
    key: BasisScopeKey
    role: ContextSelectionRole
    selected_root: ContextRootRef
    selection_act_id: UUID | None
    relationship_basis: str | None


@dataclass(frozen=True, slots=True)
class PortfolioContextUniverse:
    key: BasisScopeKey
    role: ContextSelectionRole
    selection_act_id: UUID | None
    relationship_basis: str | None


@dataclass(frozen=True, slots=True)
class PortfolioContextProvenance:
    act_id: UUID
    known_at: datetime
    basis: str


@dataclass(frozen=True, slots=True)
class PortfolioContextAbsenceMeaning:
    role: ContextSelectionRole
    selection_act_id: UUID | None
    relationship_basis: str | None


class PortfolioContextHistoryStore(Protocol):
    async def load(self) -> PortfolioContextHistory: ...

    async def append(
        self, commit: PortfolioContextCommit, *, expected_last_commit: UUID | None
    ) -> PortfolioContextHistory: ...


class PortfolioContextStoreUnavailable(Exception):
    """The Portfolio owner store cannot read or atomically append history."""


class PortfolioContextConflict(Exception):
    """The owner history advanced concurrently with this commit."""


class CanonicalPortfolioStateReader(Protocol):
    async def get(
        self, state_id: PortfolioStateId
    ) -> RecordedPortfolioState | None: ...


class PortfolioContextOwner:
    """Issue revisions through owner history and attest exact `(T,K)` selections."""

    def __init__(
        self,
        store: PortfolioContextHistoryStore,
        state_reader: CanonicalPortfolioStateReader | None = None,
    ) -> None:
        self._store = store
        self._state_reader = state_reader

    async def commit(self, act: PortfolioContextCommit) -> PortfolioContextHistory:
        for fact in act.facts:
            if isinstance(fact.meaning, ActualPortfolioStateMeaning):
                if self._state_reader is None:
                    raise ValueError("canonical Portfolio State reader is required")
                canonical = await self._state_reader.get(fact.reference.root)
                if canonical != fact.meaning.recorded:
                    raise ValueError("actual State context must match canonical State")
        history = await self._store.load()
        history.append(act)
        expected = history.commits[-1].commit_id if history.commits else None
        return await self._store.append(act, expected_last_commit=expected)

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ResolvedContextSelection[object, object, object, object] | ContextNoBasis:
        if type(key) is not BasisScopeKey or role not in PORTFOLIO_CONTEXT_ROLES:
            raise TypeError("Portfolio owner supports only its five typed roles")
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        no_basis = partial(ContextNoBasis, key, role, effective_at, known_at)
        try:
            history = await self._store.load()
        except PortfolioContextStoreUnavailable as error:
            return no_basis(ContextNoBasisReason.UNAVAILABLE_AUTHORITY, str(error))
        except InvalidPortfolioContextHistory as error:
            return no_basis(ContextNoBasisReason.INVALID_HISTORY, str(error))
        try:
            result = _selection_at(history, key, role, effective_at, known_at)
        except InvalidPortfolioContextHistory as error:
            return no_basis(ContextNoBasisReason.INVALID_HISTORY, str(error))
        if (
            role is ContextSelectionRole.ACTUAL_PORTFOLIO_STATE
            and isinstance(result, ResolvedContextSelection)
            and result.facts
        ):
            if self._state_reader is None:
                return no_basis(
                    ContextNoBasisReason.UNAVAILABLE_AUTHORITY,
                    "canonical Portfolio State reader is unavailable",
                )
            try:
                for fact in result.facts:
                    canonical = await self._state_reader.get(fact.reference.root)
                    if (
                        not isinstance(fact.fact, ActualPortfolioStateMeaning)
                        or canonical != fact.fact.recorded
                    ):
                        return no_basis(
                            ContextNoBasisReason.INVALID_HISTORY,
                            "actual State context contradicts canonical State",
                        )
            except PortfolioStateStoreFailure as error:
                return no_basis(ContextNoBasisReason.UNAVAILABLE_AUTHORITY, str(error))
        return result


def _selection_at(
    history: PortfolioContextHistory,
    key: BasisScopeKey,
    role: ContextSelectionRole,
    effective_at: datetime,
    known_at: datetime,
) -> ResolvedContextSelection[object, object, object, object] | ContextNoBasis:
    no_basis = partial(ContextNoBasis, key, role, effective_at, known_at)
    selections = (
        item
        for commit in history.commits
        if commit.known_at <= known_at
        for item in commit.selections
        if item.key == key and item.role == role and item.effective_at <= effective_at
    )
    selected = max(selections, key=lambda item: item.effective_at, default=None)
    roots = frozenset() if selected is None else selected.selected
    facts: list[SelectedContextFact[object, object, object, object]] = []
    expected_ref = _REFERENCE_BY_ROLE[role]
    for root in sorted(roots, key=repr):
        acts = (
            item
            for commit in history.commits
            if commit.known_at <= known_at
            for item in commit.facts
            if context_root(item.reference) == root
            and item.effective_at <= effective_at
        )
        fact = max(acts, key=lambda item: item.known_at, default=None)
        if fact is None:
            return no_basis(
                ContextNoBasisReason.INCOMPLETE_MEMBERSHIP,
                "selected Portfolio root has no owner fact at this boundary",
            )
        if type(fact.reference) is not expected_ref:
            raise InvalidPortfolioContextHistory("selected root has wrong family")
        if fact.contested:
            return no_basis(
                ContextNoBasisReason.CONTESTED,
                "selected Portfolio meaning is contested",
            )
        lineage = tuple(
            item.act_id
            for commit in history.commits
            if commit.known_at <= known_at
            for item in commit.facts
            if context_root(item.reference) == root and item.known_at <= fact.known_at
        )
        meaning = fact.meaning
        if isinstance(meaning, InvestmentMandateMeaning):
            applicable = tuple(
                member
                for member in meaning.members
                if member.effective_from <= effective_at
                and (
                    member.effective_until is None
                    or effective_at < member.effective_until
                )
            )
            references = {member.reference for member in applicable}
            if any(
                dependency not in references
                for member in applicable
                for dependency in member.depends_on
            ):
                return no_basis(
                    ContextNoBasisReason.INCOMPLETE_MEMBERSHIP,
                    "applicable Mandate member depends on absent member",
                )
            meaning = InvestmentMandateMeaning(meaning.portfolio_id, applicable)
        facts.append(
            SelectedContextFact(
                fact.reference,
                meaning,
                lineage,
                fact.effective_at,
                PortfolioContextProvenance(fact.act_id, fact.known_at, fact.basis),
                fact.contributions,
            )
        )
    selection_id = None if selected is None else selected.act_id
    relationship_basis = None if selected is None else selected.relationship_basis
    # duplicate-code: owner guards and test expectations are independent.
    # arid: disable
    guard = ContextSelectionGuard(
        key,
        role,
        roots,
        frozenset(
            PortfolioContextRelationship(
                key, role, root, selection_id, relationship_basis
            )
            for root in roots
        ),
        PortfolioContextUniverse(key, role, selection_id, relationship_basis),
    )
    # arid: enable
    return ResolvedContextSelection(
        key, role, effective_at, known_at, tuple(facts), guard
    )


_NO_BASIS_REASON = {
    ContextNoBasisReason.MISSING_REQUIRED: OwnerMeaningNoBasisReason.MISSING,
    ContextNoBasisReason.INCOMPLETE_MEMBERSHIP: OwnerMeaningNoBasisReason.INCOMPLETE,
    ContextNoBasisReason.CONTESTED: OwnerMeaningNoBasisReason.CONTESTED,
    ContextNoBasisReason.INVALID_HISTORY: OwnerMeaningNoBasisReason.INVALID_HISTORY,
    ContextNoBasisReason.UNAVAILABLE_AUTHORITY: OwnerMeaningNoBasisReason.UNAVAILABLE,
}


class PortfolioContextMeaningReader:
    """Attest and revalidate Portfolio context meaning against owner history."""

    def __init__(
        self,
        store: PortfolioContextHistoryStore,
        state_reader: CanonicalPortfolioStateReader | None = None,
    ) -> None:
        self._store = store
        self._owner = PortfolioContextOwner(store, state_reader)

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> OwnerMeaningWitness | OwnerMeaningNoBasis:
        if type(subject) not in (CanonicalContextMeaning, CanonicalContextAbsence):
            raise TypeError("Portfolio context meaning needs a context subject")
        if subject.role not in PORTFOLIO_CONTEXT_ROLES:
            raise TypeError("Portfolio context meaning needs a Portfolio role")
        _aware(read_at, "read_at")
        no_basis = partial(
            OwnerMeaningNoBasis, key, subject, effective_at, known_at, read_at
        )
        result = await self._owner.read_at(
            key, subject.role, effective_at=effective_at, known_at=known_at
        )
        if isinstance(result, ContextNoBasis):
            return no_basis(_NO_BASIS_REASON[result.reason], result.detail)
        if result.guard != subject.selection:
            return no_basis(
                OwnerMeaningNoBasisReason.INVALID_HISTORY,
                "Portfolio owner selection differs from requested witness",
            )
        if isinstance(subject, CanonicalContextMeaning):
            fact = next(
                (item for item in result.facts if item.reference == subject.reference),
                None,
            )
            if fact is None:
                return no_basis(
                    OwnerMeaningNoBasisReason.MISSING,
                    "selected Portfolio fact is absent",
                )
            meaning: object = fact.fact
            provenance: object = fact.provenance
            root = context_root(fact.reference)
        else:
            if result.facts:
                return no_basis(
                    OwnerMeaningNoBasisReason.INVALID_HISTORY,
                    "Portfolio absence contradicts selected facts",
                )
            meaning = PortfolioContextAbsenceMeaning(
                subject.role,
                result.guard.universe.selection_act_id,
                result.guard.universe.relationship_basis,
            )
            provenance = result.guard.universe
            root = None
        try:
            history = await self._store.load()
        except PortfolioContextStoreUnavailable:
            return no_basis(
                OwnerMeaningNoBasisReason.UNAVAILABLE,
                "Portfolio context owner history unavailable",
            )
        except InvalidPortfolioContextHistory:
            return no_basis(
                OwnerMeaningNoBasisReason.INVALID_HISTORY,
                "Portfolio context owner history is invalid",
            )
        fact_ancestry = tuple(
            OwnerHistoryRecord(item, item.effective_at, item.known_at)
            for commit in history.commits
            if commit.known_at <= known_at
            for item in commit.facts
            if root is not None and context_root(item.reference) == root
        )
        selection_ancestry = tuple(
            OwnerHistoryRecord(item, item.effective_at, item.known_at)
            for commit in history.commits
            if commit.known_at <= known_at
            for item in commit.selections
            if item.key == key and item.role == subject.role
        )
        # duplicate-code: Portfolio and Decision attest separate histories.
        # arid: disable
        return OwnerMeaningWitness(
            key,
            subject,
            effective_at,
            known_at,
            read_at,
            meaning,
            provenance,
            OwnerMeaningCause(
                fact_ancestry,
                selection_ancestry,
                (result.guard,),
                True,
            ),
        )
        # arid: enable

    async def verify_cause(
        self, witness: OwnerMeaningWitness, *, validation_at: datetime
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason:
        _aware(validation_at, "validation_at")
        if type(witness) is not OwnerMeaningWitness:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        if validation_at < witness.read_at:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        try:
            # duplicate-code: Portfolio cause replay uses its own history.
            # arid: disable
            reconstructed = await self.read_at(
                witness.key,
                witness.subject,
                effective_at=witness.effective_at,
                known_at=witness.known_at,
                read_at=witness.read_at,
            )
            # arid: enable
        except InvalidPortfolioContextHistory:
            return OwnerMeaningNoBasisReason.INVALID_HISTORY
        if isinstance(reconstructed, OwnerMeaningNoBasis):
            return reconstructed.reason
        return (
            OwnerCauseVerdict.VALID
            if reconstructed == witness
            else OwnerMeaningNoBasisReason.INVALID_HISTORY
        )
