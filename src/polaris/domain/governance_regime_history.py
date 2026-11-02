"""Governance-owned history of one R3 Investment Authority Regime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from polaris.domain.actors import KnownActorAttribution
from polaris.domain.evidence.context_versions import (
    InvestmentAuthorityRegimeId,
    InvestmentAuthorityRegimeRevision,
    InvestmentAuthorityRegimeVersionRef,
)

from .governance_authority import InvestmentAuthorityRegime


class InvalidAuthorityRegimeHistory(ValueError):
    """The regime's immutable owner history is incomplete or contradictory."""


class AuthorityRegimeNeedsReevaluation(RuntimeError):
    """Time activated owner meaning after the last revision-issuing commit."""


class AuthorityRegimeStatus(StrEnum):
    # duplicate-code: Authority correction status and draft fields are Governance-owned;
    # sharing with Evidence corrections or committed state would conflate different
    # acts.
    # arid: disable
    DETERMINATE = "determinate"
    WITHDRAWN = "withdrawn"
    CONTESTED = "contested"


@dataclass(frozen=True, slots=True)
class AuthorityRegimeCorrectionDraft:
    correction_id: UUID
    root: InvestmentAuthorityRegimeId
    attribution: KnownActorAttribution
    basis: str
    effective_at: datetime
    # arid: enable
    status: AuthorityRegimeStatus
    replacement: InvestmentAuthorityRegime | None

    def __post_init__(self) -> None:
        if type(self.correction_id) is not UUID or self.correction_id.version != 4:
            raise ValueError("correction_id must be UUIDv4")
        if type(self.root) is not InvestmentAuthorityRegimeId:
            raise TypeError("root must be InvestmentAuthorityRegimeId")
        if type(self.attribution) is not KnownActorAttribution:
            raise TypeError("correction requires an attributable human actor")
        if not isinstance(self.basis, str) or not self.basis.strip():
            raise ValueError("correction basis must be substantive")
        _aware(self.effective_at)
        if type(self.status) is not AuthorityRegimeStatus:
            raise TypeError("correction status must be closed")
        if (self.status is AuthorityRegimeStatus.DETERMINATE) != (
            type(self.replacement) is InvestmentAuthorityRegime
        ):
            raise ValueError("determinate correction requires a complete regime")
        if self.replacement is not None and self.replacement.regime_id != self.root:
            raise InvalidAuthorityRegimeHistory("correction changes regime root")

    def at_boundary(self, committed_at: datetime) -> AuthorityRegimeCorrection:
        _aware(committed_at)
        return AuthorityRegimeCorrection(
            self.correction_id,
            self.root,
            # duplicate-code: Regime correction boundary and target correction boundary
            # construct different owner acts.
            # arid: disable
            self.attribution,
            self.basis.strip(),
            self.effective_at,
            committed_at,
            # arid: enable
            self.status,
            self.replacement,
        )


@dataclass(frozen=True, slots=True)
class AuthorityRegimeCorrection:
    correction_id: UUID
    root: InvestmentAuthorityRegimeId
    attribution: KnownActorAttribution
    basis: str
    effective_at: datetime
    known_at: datetime
    status: AuthorityRegimeStatus
    replacement: InvestmentAuthorityRegime | None


@dataclass(frozen=True, slots=True)
class AuthorityRegimeSelection:
    reference: InvestmentAuthorityRegimeVersionRef
    status: AuthorityRegimeStatus
    regime: InvestmentAuthorityRegime | None
    support: tuple[UUID, ...]
    effective_at: datetime
    known_at: datetime


@dataclass(frozen=True, slots=True)
class AuthorityRegimeHistory:
    root: InvestmentAuthorityRegime
    root_known_at: datetime
    corrections: tuple[AuthorityRegimeCorrection, ...]
    revisions: tuple[InvestmentAuthorityRegimeRevision, ...]

    @classmethod
    def form(
        cls, regime: InvestmentAuthorityRegime, committed_at: datetime
    ) -> AuthorityRegimeHistory:
        if type(regime) is not InvestmentAuthorityRegime:
            raise TypeError("root must be InvestmentAuthorityRegime")
        _aware(committed_at)
        return cls(regime, committed_at, (), (InvestmentAuthorityRegimeRevision(1),))

    def __post_init__(self) -> None:
        if len(self.revisions) != len(self.corrections) + 1:
            raise InvalidAuthorityRegimeHistory("revision history is incomplete")
        if self.revisions[0].value != 1:
            raise InvalidAuthorityRegimeHistory("root revision must begin at 1")

    def append(self, correction: AuthorityRegimeCorrection) -> AuthorityRegimeHistory:
        if type(correction) is not AuthorityRegimeCorrection:
            raise TypeError("correction must be an owner act")
        if correction.root != self.root.regime_id:
            raise InvalidAuthorityRegimeHistory("correction changes regime root")
        last = self.corrections[-1].known_at if self.corrections else self.root_known_at
        if correction.known_at < last:
            raise InvalidAuthorityRegimeHistory("owner commits are unordered")
        if correction.correction_id in {act.correction_id for act in self.corrections}:
            raise InvalidAuthorityRegimeHistory("correction identity is repeated")
        prior = self._select(last, last)
        candidate = AuthorityRegimeHistory(
            self.root,
            self.root_known_at,
            (*self.corrections, correction),
            (*self.revisions, self.revisions[-1]),
        )
        current = candidate._select(correction.known_at, correction.known_at)
        changed = (prior.status, prior.regime, prior.support) != (
            current.status,
            current.regime,
            current.support,
        )
        revision = InvestmentAuthorityRegimeRevision(
            self.revisions[-1].value + int(changed)
        )
        return AuthorityRegimeHistory(
            self.root,
            self.root_known_at,
            candidate.corrections,
            (*self.revisions, revision),
        )

    def select(
        self, effective_at: datetime, known_at: datetime
    ) -> AuthorityRegimeSelection | None:
        selection = self._select(effective_at, known_at)
        if selection is None:
            return None
        if effective_at == known_at:
            known = tuple(act for act in self.corrections if act.known_at <= known_at)
            last = known[-1].known_at if known else self.root_known_at
            if last < known_at:
                prior = self._select(last, last)
                if prior is not None and (
                    prior.status,
                    prior.regime,
                    prior.support,
                ) != (selection.status, selection.regime, selection.support):
                    raise AuthorityRegimeNeedsReevaluation(
                        "time changed authority meaning after its last owner commit"
                    )
        return selection

    def _select(
        self, effective_at: datetime, known_at: datetime
    ) -> AuthorityRegimeSelection | None:
        _aware(effective_at)
        _aware(known_at)
        if known_at < self.root_known_at:
            return None
        known = tuple(act for act in self.corrections if act.known_at <= known_at)
        active = tuple(act for act in known if act.effective_at <= effective_at)
        current = active[-1] if active else None
        status = (
            AuthorityRegimeStatus.DETERMINATE if current is None else current.status
        )
        regime = self.root if current is None else current.replacement
        revision = self.revisions[len(known)]
        return AuthorityRegimeSelection(
            InvestmentAuthorityRegimeVersionRef(self.root.regime_id, revision),
            status,
            regime,
            tuple(act.correction_id for act in active),
            effective_at,
            known_at,
        )


def _aware(value: datetime) -> None:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise ValueError("authority history time must be timezone-aware")
