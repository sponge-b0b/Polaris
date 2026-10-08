"""Inward reads of owner-issued R3 context selection and historical meaning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    CanonicalContextVersionRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    _validate_selection_scope,
    context_root,
    is_canonical_context_version_ref,
)


class ContextContribution(StrEnum):
    APPLICABILITY = "applicability"
    RESULT = "result"
    SUPPORT = "support"
    PROVENANCE = "provenance"


@dataclass(frozen=True, slots=True)
class SelectedContextFact[FactT, LineageT, ApplicabilityT, ProvenanceT]:
    """One owner fact and the meaning needed to reconstruct its selected version.

    Payload types are supplied by the owning domain. Application preserves them;
    it neither issues versions nor takes ownership of the underlying fact.
    """

    reference: CanonicalContextVersionRef
    fact: FactT
    lineage: LineageT
    applicability: ApplicabilityT
    provenance: ProvenanceT
    contributions: frozenset[ContextContribution]

    def __post_init__(self) -> None:
        if not is_canonical_context_version_ref(self.reference):
            raise TypeError("reference must be CanonicalContextVersionRef")
        if any(
            value is None
            for value in (self.fact, self.lineage, self.applicability, self.provenance)
        ):
            raise ValueError(
                "owner fact, lineage, applicability and provenance are required"
            )
        if (
            type(self.contributions) is not frozenset
            or not self.contributions
            or any(type(item) is not ContextContribution for item in self.contributions)
        ):
            raise ValueError("at least one material ContextContribution is required")


@dataclass(frozen=True, slots=True)
class _ContextReadIdentity:
    key: BasisScopeKey
    role: ContextSelectionRole
    effective_at: datetime
    known_at: datetime

    def __post_init__(self) -> None:
        _validate_selection_scope(self.key, self.role)
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")


@dataclass(frozen=True, slots=True)
class ResolvedContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT](
    _ContextReadIdentity
):
    """Owner attestation of the full current selected set, including no fact."""

    facts: tuple[SelectedContextFact[FactT, LineageT, ApplicabilityT, ProvenanceT], ...]
    guard: ContextSelectionGuard

    def __post_init__(self) -> None:
        _ContextReadIdentity.__post_init__(self)
        if type(self.facts) is not tuple:
            raise TypeError("facts must be a tuple")
        if any(type(fact) is not SelectedContextFact for fact in self.facts):
            raise TypeError("facts must contain SelectedContextFact")
        if type(self.guard) is not ContextSelectionGuard:
            raise TypeError("guard must be ContextSelectionGuard")
        if self.guard.key != self.key or self.guard.role != self.role:
            raise ValueError("guard must match exact key and role")
        if self.guard.selected != frozenset(
            context_root(fact.reference) for fact in self.facts
        ):
            raise ValueError("guard must cover every selected owner fact")
        if len(self.guard.selected) != len(self.facts):
            raise ValueError("owner facts must have unique references")


class ContextNoBasisReason(StrEnum):
    MISSING_REQUIRED = "missing_required"
    INCOMPLETE_MEMBERSHIP = "incomplete_membership"
    CONTESTED = "contested"
    INVALID_HISTORY = "invalid_history"
    UNAVAILABLE_AUTHORITY = "unavailable_authority"


@dataclass(frozen=True, slots=True)
class ContextNoBasis(_ContextReadIdentity):
    reason: ContextNoBasisReason
    detail: str

    def __post_init__(self) -> None:
        _ContextReadIdentity.__post_init__(self)
        if type(self.reason) is not ContextNoBasisReason:
            raise TypeError("reason must be ContextNoBasisReason")


type ContextOwnerResult[FactT, LineageT, ApplicabilityT, ProvenanceT] = (
    ResolvedContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT]
    | ContextNoBasis
)


class ContextOwnerReadUnavailable(Exception):
    """An authoritative context owner could not complete its read."""


class ContextOwnerReader[FactT, LineageT, ApplicabilityT, ProvenanceT](Protocol):
    """Read complete role membership from its owner at exact `(T,K)`.

    A resolved empty set is an authoritative absence. Missing required facts,
    incomplete relationship membership, contestation, invalid history and source
    unavailability must instead return distinct ContextNoBasis outcomes. Owner
    revisions start at 1 and advance once per commit that changes current
    interpretation, applicability, support/provenance or validity. Fresh as-of
    Portfolio State and other new attributable facts use new roots. The Mandate
    revision covers applicable Objective/Principle membership and exact members.
    Future-only, out-of-key and presentation-only facts are excluded from current
    selection; historical meaning is resolved at its own `(T,K)` boundary.
    """

    async def read_at(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ContextOwnerResult[FactT, LineageT, ApplicabilityT, ProvenanceT]: ...


@dataclass(frozen=True, slots=True)
class CompleteContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT]:
    """Exactly one complete owner result for every closed R3 context role."""

    key: BasisScopeKey
    at: datetime
    selections: tuple[
        ResolvedContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT], ...
    ]

    def __post_init__(self) -> None:
        if type(self.key) is not BasisScopeKey:
            raise TypeError("key must be BasisScopeKey")
        _aware(self.at, "at")
        if type(self.selections) is not tuple:
            raise TypeError("selections must be a tuple")
        if tuple(selection.role for selection in self.selections) != tuple(
            ContextSelectionRole
        ):
            raise ValueError("selections must cover every R3 role exactly once")
        if any(
            selection.key != self.key
            or selection.effective_at != self.at
            or selection.known_at != self.at
            for selection in self.selections
        ):
            raise ValueError("selections must match exact key and current T=K")

    @property
    def positive_references(self) -> tuple[CanonicalContextVersionRef, ...]:
        return tuple(
            fact.reference for selection in self.selections for fact in selection.facts
        )

    @property
    def guards(self) -> tuple[ContextSelectionGuard, ...]:
        return tuple(selection.guard for selection in self.selections)


class ContextSelectionResolver[FactT, LineageT, ApplicabilityT, ProvenanceT]:
    """Admit only complete exact owner results, without synthesizing absences."""

    def __init__(
        self, owner: ContextOwnerReader[FactT, LineageT, ApplicabilityT, ProvenanceT]
    ) -> None:
        self._owner = owner

    async def read_historical(
        self,
        key: BasisScopeKey,
        role: ContextSelectionRole,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ContextOwnerResult[FactT, LineageT, ApplicabilityT, ProvenanceT]:
        identity = _ContextReadIdentity(key, role, effective_at, known_at)
        try:
            result = await self._owner.read_at(
                key, role, effective_at=effective_at, known_at=known_at
            )
        except ContextOwnerReadUnavailable as error:
            return _no_basis(
                identity,
                ContextNoBasisReason.UNAVAILABLE_AUTHORITY,
                str(error),
            )
        if (
            isinstance(result, (ResolvedContextSelection, ContextNoBasis))
            and result.key == key
            and result.role == role
            and result.effective_at == effective_at
            and result.known_at == known_at
        ):
            return result
        return _no_basis(
            identity,
            ContextNoBasisReason.INVALID_HISTORY,
            "owner result mismatch",
        )

    async def read_current(
        self, key: BasisScopeKey, role: ContextSelectionRole, *, at: datetime
    ) -> ContextOwnerResult[FactT, LineageT, ApplicabilityT, ProvenanceT]:
        return await self.read_historical(key, role, effective_at=at, known_at=at)

    async def read_complete_current(
        self, key: BasisScopeKey, *, at: datetime
    ) -> (
        CompleteContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT]
        | ContextNoBasis
    ):
        selections: list[
            ResolvedContextSelection[FactT, LineageT, ApplicabilityT, ProvenanceT]
        ] = []
        for role in ContextSelectionRole:
            result = await self.read_current(key, role, at=at)
            if isinstance(result, ContextNoBasis):
                return result
            selections.append(result)
        return CompleteContextSelection(key, at, tuple(selections))


def _no_basis(
    identity: _ContextReadIdentity,
    reason: ContextNoBasisReason,
    detail: str,
) -> ContextNoBasis:
    return ContextNoBasis(
        identity.key,
        identity.role,
        identity.effective_at,
        identity.known_at,
        reason,
        detail,
    )


# duplicate-code: the context-owner read boundary validates query time without
# importing Decisions-domain validation or conflating owner failure types.
# arid: disable
def _aware(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
