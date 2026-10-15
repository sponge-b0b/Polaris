"""Inward contract for owner-attested as-of meaning and temporal cause."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from polaris.domain.evidence.claims import ClaimCatalogVersion
from polaris.domain.evidence.context_versions import (
    BasisScopeKey,
    CanonicalContextVersionRef,
    ContextSelectionGuard,
    ContextSelectionRole,
    DecisionContextVersionRef,
    context_root,
    is_canonical_context_version_ref,
)
from polaris.domain.evidence.judgment_versions import (
    TargetJudgmentVersionRef,
    is_target_judgment_version_ref,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    ClaimSpecificEvidenceScope,
    EvidenceJudgmentRef,
    is_evidence_judgment_ref,
)


@dataclass(frozen=True, slots=True)
class GoverningDecisionMeaning:
    reference: DecisionContextVersionRef


@dataclass(frozen=True, slots=True)
class TargetJudgmentMeaning:
    reference: TargetJudgmentVersionRef


@dataclass(frozen=True, slots=True)
class ClaimMembershipMeaning:
    target: EvidenceJudgmentRef
    claim_id: ClaimId
    catalog_version: ClaimCatalogVersion

    def __post_init__(self) -> None:
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("claim target must be EvidenceJudgmentRef")
        if type(self.claim_id) is not ClaimId:
            raise TypeError("claim_id must be ClaimId")
        if type(self.catalog_version) is not ClaimCatalogVersion:
            raise TypeError("catalog_version must be ClaimCatalogVersion")


@dataclass(frozen=True, slots=True)
class CanonicalContextMeaning:
    role: ContextSelectionRole
    reference: CanonicalContextVersionRef
    selection: ContextSelectionGuard

    def __post_init__(self) -> None:
        if not is_canonical_context_version_ref(self.reference):
            raise TypeError("context reference must be a canonical typed version")
        _validate_context_selection(self.role, self.selection)
        if (
            self.selection.role is not self.role
            or context_root(self.reference) not in self.selection.selected
        ):
            raise ValueError("context reference must be selected under its role")


@dataclass(frozen=True, slots=True)
class CanonicalContextAbsence:
    """Typed owner attestation that a role has no selected fact at this key."""

    role: ContextSelectionRole
    selection: ContextSelectionGuard

    def __post_init__(self) -> None:
        _validate_context_selection(self.role, self.selection)
        if self.selection.role is not self.role or self.selection.selected:
            raise ValueError("context absence requires an empty selected role")


def _validate_context_selection(
    role: ContextSelectionRole, selection: ContextSelectionGuard
) -> None:
    if type(role) is not ContextSelectionRole:
        raise TypeError("context role must be ContextSelectionRole")
    if type(selection) is not ContextSelectionGuard:
        raise TypeError("context selection must be ContextSelectionGuard")


type OwnerMeaningSubject = (
    GoverningDecisionMeaning
    | TargetJudgmentMeaning
    | ClaimMembershipMeaning
    | CanonicalContextMeaning
    | CanonicalContextAbsence
)


@dataclass(frozen=True, slots=True)
class OwnerHistoryRecord[FactT]:
    """An owner fact or correction with its two independent temporal boundaries."""

    fact: FactT
    effective_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if self.fact is None:
            raise ValueError("history fact cannot be absent")
        _aware(self.effective_at)
        _aware(self.recorded_at)


@dataclass(frozen=True, slots=True)
class OwnerMeaningCause[FactT, CorrectionT, GuardT]:
    """Owner-supplied complete ancestry and selected-or-absent relationships.

    The owning domain verifies entailment against its authoritative history.
    Application does not interpret these owner-specific facts or guards.
    """

    fact_ancestry: tuple[OwnerHistoryRecord[FactT], ...]
    correction_ancestry: tuple[OwnerHistoryRecord[CorrectionT], ...]
    relationship_guards: tuple[GuardT, ...]
    complete: bool

    def __post_init__(self) -> None:
        if (
            type(self.fact_ancestry) is not tuple
            or type(self.correction_ancestry) is not tuple
            or type(self.relationship_guards) is not tuple
        ):
            raise TypeError("owner ancestry and guards must be tuples")
        if any(
            type(item) is not OwnerHistoryRecord
            for item in (*self.fact_ancestry, *self.correction_ancestry)
        ):
            raise TypeError("owner ancestry must carry temporal history records")
        if any(guard is None for guard in self.relationship_guards):
            raise ValueError("relationship guards cannot contain absent values")
        if not self.relationship_guards:
            raise ValueError("owner cause requires selected-or-absent guards")
        if type(self.complete) is not bool:
            raise TypeError("owner completeness must be explicit")


@dataclass(frozen=True, slots=True)
class _OwnerReadIdentity:
    key: BasisScopeKey
    subject: OwnerMeaningSubject
    effective_at: datetime
    known_at: datetime
    read_at: datetime

    def __post_init__(self) -> None:
        if type(self.key) is not BasisScopeKey:
            raise TypeError("owner meaning requires BasisScopeKey")
        _subject_for_key(self.subject, self.key)
        for value in (self.effective_at, self.known_at, self.read_at):
            _aware(value)
        if self.known_at > self.read_at:
            raise ValueError("read cannot precede its knowledge cutoff")


@dataclass(frozen=True, slots=True)
class OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT](
    _OwnerReadIdentity
):
    """Exact typed owner interpretation at one effective, known and read boundary."""

    meaning: MeaningT
    provenance: ProvenanceT
    cause: OwnerMeaningCause[FactT, CorrectionT, GuardT]

    def __post_init__(self) -> None:
        _OwnerReadIdentity.__post_init__(self)
        if self.meaning is None or self.provenance is None:
            raise ValueError("owner meaning and provenance are required")
        if type(self.cause) is not OwnerMeaningCause:
            raise TypeError("owner cause must be OwnerMeaningCause")
        if not self.cause.complete:
            raise ValueError("incomplete cause cannot be a resolved witness")
        if isinstance(self.subject, (CanonicalContextMeaning, CanonicalContextAbsence)):
            if self.subject.selection not in self.cause.relationship_guards:
                raise ValueError("context cause must retain its selection guard")
        if any(
            item.recorded_at > self.known_at
            for item in (*self.cause.fact_ancestry, *self.cause.correction_ancestry)
        ):
            raise ValueError("history recorded after the cutoff cannot support meaning")

    @property
    def semantic_identity(self) -> tuple[object, ...]:
        """Compare attested meaning; owner cause proves it independently."""
        return (
            self.key,
            self.subject,
            self.meaning,
            self.provenance,
        )


class OwnerMeaningNoBasisReason(StrEnum):
    MISSING = "missing"
    INCOMPLETE = "incomplete"
    CONTESTED = "contested"
    NOT_YET_EFFECTIVE = "not_yet_effective"
    UNAVAILABLE = "unavailable"
    CONTRADICTORY = "contradictory"
    INVALID_HISTORY = "invalid_history"


@dataclass(frozen=True, slots=True)
class OwnerMeaningNoBasis(_OwnerReadIdentity):
    reason: OwnerMeaningNoBasisReason
    detail: str

    def __post_init__(self) -> None:
        _OwnerReadIdentity.__post_init__(self)
        if type(self.reason) is not OwnerMeaningNoBasisReason:
            raise TypeError("no-basis reason must be typed")


class OwnerCauseVerdict(StrEnum):
    VALID = "valid"


class OwnerMeaningReadUnavailable(Exception):
    """The authoritative owner cannot read or verify its history."""


class OwnerMeaningReader[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT](Protocol):
    """Owner reads and verifies cause against complete authoritative history."""

    async def read_at(
        self,
        key: BasisScopeKey,
        subject: OwnerMeaningSubject,
        *,
        effective_at: datetime,
        known_at: datetime,
        read_at: datetime,
    ) -> (
        OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT]
        | OwnerMeaningNoBasis
    ): ...

    async def verify_cause(
        self,
        witness: OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT],
        *,
        validation_at: datetime,
    ) -> OwnerCauseVerdict | OwnerMeaningNoBasisReason: ...


class OwnerMeaningResolver[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT]:
    """Admit only exact, owner-verified proof; never invent owner history."""

    def __init__(
        self,
        owner: OwnerMeaningReader[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT],
    ) -> None:
        self._owner = owner

    async def read_current(
        self, key: BasisScopeKey, subject: OwnerMeaningSubject, *, at: datetime
    ) -> (
        OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT]
        | OwnerMeaningNoBasis
    ):
        _subject_for_key(subject, key)
        _aware(at)
        try:
            result = await self._owner.read_at(
                key, subject, effective_at=at, known_at=at, read_at=at
            )
        except OwnerMeaningReadUnavailable as error:
            return _at_no_basis(
                key, subject, at, OwnerMeaningNoBasisReason.UNAVAILABLE, str(error)
            )
        if (
            type(result) not in (OwnerMeaningWitness, OwnerMeaningNoBasis)
            or result.key != key
            or result.subject != subject
            or result.effective_at != at
            or result.known_at != at
            or result.read_at != at
        ):
            return _at_no_basis(
                key,
                subject,
                at,
                OwnerMeaningNoBasisReason.INVALID_HISTORY,
                "owner result did not match the requested key and boundary",
            )
        if isinstance(result, OwnerMeaningNoBasis):
            return result
        return await self.verify(result, validation_at=at)

    async def verify(
        self,
        witness: OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT],
        *,
        validation_at: datetime,
    ) -> (
        OwnerMeaningWitness[MeaningT, ProvenanceT, FactT, CorrectionT, GuardT]
        | OwnerMeaningNoBasis
    ):
        _aware(validation_at)
        try:
            verdict = await self._owner.verify_cause(
                witness, validation_at=validation_at
            )
        except OwnerMeaningReadUnavailable as error:
            verdict = OwnerMeaningNoBasisReason.UNAVAILABLE
            detail = str(error)
        else:
            detail = "owner cause could not be verified"
        if verdict is OwnerCauseVerdict.VALID:
            return witness
        reason = (
            verdict
            if type(verdict) is OwnerMeaningNoBasisReason
            else OwnerMeaningNoBasisReason.INVALID_HISTORY
        )
        return OwnerMeaningNoBasis(
            witness.key,
            witness.subject,
            witness.effective_at,
            witness.known_at,
            witness.read_at,
            reason,
            detail,
        )


def _at_no_basis(
    key: BasisScopeKey,
    subject: OwnerMeaningSubject,
    at: datetime,
    reason: OwnerMeaningNoBasisReason,
    detail: str,
) -> OwnerMeaningNoBasis:
    return OwnerMeaningNoBasis(key, subject, at, at, at, reason, detail)


def _subject_for_key(subject: OwnerMeaningSubject, key: BasisScopeKey) -> None:
    if type(key) is not BasisScopeKey:
        raise TypeError("owner meaning requires BasisScopeKey")
    if type(subject) is GoverningDecisionMeaning:
        if (
            type(subject.reference) is not DecisionContextVersionRef
            or subject.reference.root != key.decision_id
        ):
            raise ValueError("governing Decision must match the exact key")
    elif type(subject) is TargetJudgmentMeaning:
        if (
            not is_target_judgment_version_ref(subject.reference)
            or subject.reference.root != key.target
        ):
            raise ValueError("target judgment must match the exact key")
    elif type(subject) is ClaimMembershipMeaning:
        _claim_subject_for_key(subject, key)
    elif type(subject) is CanonicalContextMeaning:
        _context_subject_for_key(subject.selection, key)
        if type(subject.reference) is DecisionContextVersionRef and (
            subject.reference.root == key.decision_id
        ):
            raise ValueError("governing Decision is not canonical context")
    elif type(subject) is CanonicalContextAbsence:
        _context_subject_for_key(subject.selection, key)
    else:
        raise TypeError("owner meaning subject must be a closed typed variant")


def _context_subject_for_key(
    selection: ContextSelectionGuard, key: BasisScopeKey
) -> None:
    if selection.key != key:
        raise ValueError("context selection must match the exact key")


def _claim_subject_for_key(subject: ClaimMembershipMeaning, key: BasisScopeKey) -> None:
    if (
        type(key.scope) is not ClaimSpecificEvidenceScope
        or subject.target != key.target
        or subject.claim_id != key.scope.claim_id
    ):
        raise ValueError("claim membership must match the exact key")


# duplicate-code: this inward Evidence owner boundary validates query instants
# independently of the Decisions-domain private validator and its error type.
# arid: disable
def _aware(value: datetime) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("owner meaning boundary must be timezone-aware")


# arid: enable
