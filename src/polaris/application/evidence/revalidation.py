"""Fresh command-basis validation inside a dependent command's write boundary."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, fields
from datetime import datetime
from typing import Protocol

from polaris.domain.evidence.context_versions import BasisScopeKey

from .current_basis import (
    CurrentEvidenceBasis,
    CurrentEvidenceBasisResult,
    CurrentEvidenceNoBasis,
    CurrentNoBasisReason,
    compare_current_evidence_bases,
)
from .reconstruction import StaleEvidenceBasis


class CurrentBasisValidationReader(Protocol):
    """Complete owner reads bound to the dependent command's write boundary."""

    async def read(
        self, key: BasisScopeKey, *, at: datetime
    ) -> CurrentEvidenceBasisResult: ...

    async def verify_owner_meaning(
        self, basis: CurrentEvidenceBasis, *, validation_at: datetime
    ) -> CurrentEvidenceNoBasis | None: ...


@dataclass(frozen=True, slots=True)
class AtomicCurrentBasisRead:
    """Owner readers and trusted instant enrolled in one dependent write boundary.

    ``query`` must use only readers participating in that boundary. It must
    cover the complete Decision, target, claim when applicable, Configuration,
    context, and Evidence owner set; a partial owner set is unavailable.
    """

    key: BasisScopeKey
    at: datetime
    query: CurrentBasisValidationReader

    def __post_init__(self) -> None:
        if type(self.key) is not BasisScopeKey:
            raise TypeError("atomic read requires the exact typed basis key")
        if self.at.tzinfo is None or self.at.utcoffset() is None:
            raise ValueError("atomic read requires a trusted aware T=K")
        if self.query is None:
            raise TypeError("atomic read requires complete current-basis readers")


class AtomicCurrentBasisParticipation(Protocol):
    """Dependent command capability, invoked while its concrete write is open.

    Return an enrolled read only when the write and every required owner reader
    share a validation boundary that excludes concurrent invalidating commits
    through the write commit. Return ``None`` when any participation, trusted
    instant, or authoritative source cannot be established. The consuming Spec
    owns the concrete write and proof of this port's atomic implementation.
    """

    async def establish(self, key: BasisScopeKey) -> AtomicCurrentBasisRead | None: ...


class AtomicCurrentBasisUnavailable(Exception):
    """An authoritative owner or the dependent write cannot join validation."""


class CurrentBasisWriteTransaction[T](AtomicCurrentBasisParticipation, Protocol):
    """One enrolled owner read and dependent write in the same atomic boundary."""

    async def write(self) -> T:
        """Persist the prepared judgment without doing external or model work."""


class CurrentBasisWriteBoundary[T](Protocol):
    """Open a transaction that excludes invalidating owner commits until exit."""

    def transaction(
        self, key: BasisScopeKey
    ) -> AbstractAsyncContextManager[CurrentBasisWriteTransaction[T]]: ...


class CurrentEvidenceBasisRevalidator:
    """Reject stale or unusable bases before a dependent command may write."""

    async def revalidate(
        self,
        prior: CurrentEvidenceBasis,
        participation: AtomicCurrentBasisParticipation,
    ) -> StaleEvidenceBasis | CurrentEvidenceNoBasis | None:
        if type(prior) is not CurrentEvidenceBasis:
            raise TypeError("revalidation requires a complete prior basis")
        try:
            enrolled = await participation.establish(prior.key)
        except AtomicCurrentBasisUnavailable as error:
            return CurrentEvidenceNoBasis(
                prior.key, prior.at, CurrentNoBasisReason.UNAVAILABLE, str(error)
            )
        if enrolled is None:
            return CurrentEvidenceNoBasis(
                prior.key,
                prior.at,
                CurrentNoBasisReason.UNAVAILABLE,
                "atomic owner and write participation could not be established",
            )
        if (
            type(enrolled) is not AtomicCurrentBasisRead
            or enrolled.key != prior.key
            or enrolled.at <= prior.at
        ):
            return CurrentEvidenceNoBasis(
                prior.key,
                prior.at,
                CurrentNoBasisReason.INVALID_HISTORY,
                "atomic read did not match the protected key and boundary",
            )

        query = enrolled.query
        prior_failure = await query.verify_owner_meaning(
            prior, validation_at=enrolled.at
        )
        if prior_failure is not None:
            return prior_failure

        reconstructed_prior = await _read_exact(
            query, prior.key, at=prior.at, report_at=enrolled.at
        )
        if isinstance(reconstructed_prior, CurrentEvidenceNoBasis):
            return reconstructed_prior
        if not _same_prior_basis(prior, reconstructed_prior):
            return CurrentEvidenceNoBasis(
                prior.key,
                enrolled.at,
                CurrentNoBasisReason.INVALID_HISTORY,
                "protected prior basis contradicts authoritative history",
            )

        fresh = await _read_exact(
            query, prior.key, at=enrolled.at, report_at=enrolled.at
        )
        if isinstance(fresh, CurrentEvidenceNoBasis):
            return fresh
        fresh_failure = await query.verify_owner_meaning(
            fresh, validation_at=enrolled.at
        )
        if fresh_failure is not None:
            return fresh_failure
        return compare_current_evidence_bases(prior, fresh)

    async def commit[T](
        self,
        prior: CurrentEvidenceBasis,
        boundary: CurrentBasisWriteBoundary[T],
    ) -> T | StaleEvidenceBasis | CurrentEvidenceNoBasis:
        """Validate the accepted basis inside the dependent write transaction.

        The caller prepares the judgment before opening the boundary. A stale or
        unusable basis never invokes ``write``; the caller must obtain a new read.
        """
        if type(prior) is not CurrentEvidenceBasis:
            raise TypeError("dependent commit requires a complete prior basis")
        async with boundary.transaction(prior.key) as transaction:
            outcome = await self.revalidate(prior, transaction)
            if outcome is not None:
                return outcome
            return await transaction.write()


def _same_prior_basis(
    prior: CurrentEvidenceBasis, reconstructed: CurrentEvidenceBasis
) -> bool:
    if any(
        getattr(prior, field.name) != getattr(reconstructed, field.name)
        for field in fields(CurrentEvidenceBasis)
        if field.name != "owner_meaning"
    ):
        return False
    old = prior.owner_meaning
    new = reconstructed.owner_meaning
    return (
        old.decision.semantic_identity == new.decision.semantic_identity
        and old.target.semantic_identity == new.target.semantic_identity
        and (old.claim.semantic_identity if old.claim is not None else None)
        == (new.claim.semantic_identity if new.claim is not None else None)
        and tuple(item.semantic_identity for item in old.context)
        == tuple(item.semantic_identity for item in new.context)
    )


async def _read_exact(
    query: CurrentBasisValidationReader,
    key: BasisScopeKey,
    *,
    at: datetime,
    report_at: datetime,
) -> CurrentEvidenceBasis | CurrentEvidenceNoBasis:
    result = await query.read(key, at=at)
    if type(result) is CurrentEvidenceBasis:
        return (
            result
            if result.key == key and result.at == at
            else _invalid_owner_result(key, report_at)
        )
    if type(result) is CurrentEvidenceNoBasis and result.key == key and result.at == at:
        return (
            result
            if at == report_at
            else CurrentEvidenceNoBasis(key, report_at, result.reason, result.detail)
        )
    return _invalid_owner_result(key, report_at)


def _invalid_owner_result(key: BasisScopeKey, at: datetime) -> CurrentEvidenceNoBasis:
    return CurrentEvidenceNoBasis(
        key,
        at,
        CurrentNoBasisReason.INVALID_HISTORY,
        "atomic owner read did not return a complete basis",
    )
