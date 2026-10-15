"""Inward read boundary for target-owned judgment versions and meaning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from polaris.domain.evidence.judgment_versions import (
    TargetJudgmentVersionRef,
    is_target_judgment_version_ref,
)
from polaris.domain.evidence.judgments import (
    EvidenceJudgmentRef,
    is_evidence_judgment_ref,
)


@dataclass(frozen=True, slots=True)
class ResolvedTargetJudgment[AssertionT, SupportT]:
    """Owner assertion and complete surviving correction support at `(T,K)`.

    The version belongs to that historical boundary. The owner alone issues it;
    consumers must not derive it from the root identity or today's version.
    """

    target: EvidenceJudgmentRef
    version: TargetJudgmentVersionRef
    assertion: AssertionT
    correction_support: tuple[SupportT, ...]
    effective_at: datetime
    known_at: datetime

    def __post_init__(self) -> None:
        if not is_evidence_judgment_ref(self.target):
            raise TypeError("target must be an EvidenceJudgmentRef")
        if not is_target_judgment_version_ref(self.version):
            raise TypeError("version must be a TargetJudgmentVersionRef")
        if self.version.root != self.target:
            raise ValueError("version root must match target")
        if self.assertion is None:
            raise ValueError("resolved owner assertion cannot be missing")
        if type(self.correction_support) is not tuple:
            raise TypeError("correction_support must be a tuple")
        _aware(self.effective_at, "effective_at")
        _aware(self.known_at, "known_at")


@dataclass(frozen=True, slots=True)
class TargetJudgmentWithdrawn:
    target: EvidenceJudgmentRef


@dataclass(frozen=True, slots=True)
class TargetJudgmentContested:
    target: EvidenceJudgmentRef
    reason: str


@dataclass(frozen=True, slots=True)
class TargetJudgmentMissing:
    target: EvidenceJudgmentRef


@dataclass(frozen=True, slots=True)
class TargetJudgmentInvalidHistory:
    target: EvidenceJudgmentRef
    reason: str


@dataclass(frozen=True, slots=True)
class TargetJudgmentUnavailable:
    target: EvidenceJudgmentRef
    reason: str


type TargetJudgmentResolution[AssertionT, SupportT] = (
    ResolvedTargetJudgment[AssertionT, SupportT]
    | TargetJudgmentWithdrawn
    | TargetJudgmentContested
    | TargetJudgmentMissing
    | TargetJudgmentInvalidHistory
    | TargetJudgmentUnavailable
)


class TargetJudgmentOwnerReadUnavailable(Exception):
    """The authoritative target owner could not answer the requested read."""


class TargetJudgmentOwnerReader[AssertionT, SupportT](Protocol):
    """Vendor-neutral owner read; never an Evidence-owned fact store.

    The owner resolves complete assertion, correction support, and validity at
    explicit `(T,K)`. At `T=K`, an eligible current read may return a version
    issued by its owner; missing, withdrawn, contested, invalid, or unavailable
    results never authorize a command basis. Owner commits advance a root once
    only when its current assertion, support/provenance, validity, or
    applicability changes at the command boundary. New judgments get new roots.
    ClaimCatalogVersion remains a separate owner contract. An unrelated later
    root leaves an exact-root read unchanged. Only an explicit owner relationship
    changing that root's meaning may advance it; a current-selection read must
    separately guard the selection that a later root could replace. Historical
    reads resolve both effective and recorded cutoffs independently and never
    substitute the owner's present revision for the earlier boundary.
    """

    async def read_at(
        self,
        target: EvidenceJudgmentRef,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> TargetJudgmentResolution[AssertionT, SupportT]: ...


class TargetJudgmentResolver[AssertionT, SupportT]:
    """Admit only an exact authoritative owner result for the requested cutoff."""

    def __init__(self, owner: TargetJudgmentOwnerReader[AssertionT, SupportT]) -> None:
        self._owner = owner

    async def read_historical(
        self,
        target: EvidenceJudgmentRef,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> TargetJudgmentResolution[AssertionT, SupportT]:
        if not is_evidence_judgment_ref(target):
            raise TypeError("target must be an EvidenceJudgmentRef")
        _aware(effective_at, "effective_at")
        _aware(known_at, "known_at")
        try:
            result = await self._owner.read_at(
                target, effective_at=effective_at, known_at=known_at
            )
        except TargetJudgmentOwnerReadUnavailable as error:
            return TargetJudgmentUnavailable(target, str(error))

        if type(result) is ResolvedTargetJudgment:
            if (
                result.target == target
                and result.effective_at == effective_at
                and result.known_at == known_at
            ):
                return result
        elif (
            type(result)
            in (
                TargetJudgmentWithdrawn,
                TargetJudgmentContested,
                TargetJudgmentMissing,
                TargetJudgmentInvalidHistory,
                TargetJudgmentUnavailable,
            )
            and result.target == target
        ):
            return result
        return TargetJudgmentInvalidHistory(target, "owner result did not match read")

    async def read_current(
        self, target: EvidenceJudgmentRef, *, at: datetime
    ) -> TargetJudgmentResolution[AssertionT, SupportT]:
        """Read `T=K`; only a resolved result may enter a guarded command basis."""
        return await self.read_historical(target, effective_at=at, known_at=at)


# duplicate-code: the owner-read application boundary validates query time with
# ValueError; sharing a Decisions-domain private validator would couple owners.
# arid: disable
def _aware(value: datetime, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
