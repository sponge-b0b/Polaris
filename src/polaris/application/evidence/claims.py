from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from polaris.domain.evidence.claims import (
    ClaimCatalogRevision,
    ClaimCatalogVersion,
    ContestedClaimCatalogHistory,
    InvalidClaimCatalogHistory,
    validate_claim_catalog_history,
)
from polaris.domain.evidence.judgments import (
    ClaimId,
    EvidenceJudgmentRef,
    is_evidence_judgment_ref,
)


class ClaimCatalogReadUnavailable(Exception):
    """Technology-neutral failure to read target-owned claim history."""


class ClaimCatalogStore(Protocol):
    async def load_claim_catalog(
        self,
        target: EvidenceJudgmentRef,
    ) -> tuple[ClaimCatalogRevision, ...]: ...


@dataclass(frozen=True, slots=True)
class ResolvedClaimMembership:
    target: EvidenceJudgmentRef
    claim_id: ClaimId
    catalog_version: ClaimCatalogVersion


@dataclass(frozen=True, slots=True)
class ClaimTargetNotKnownAtCutoff:
    target: EvidenceJudgmentRef


@dataclass(frozen=True, slots=True)
class ClaimNotKnownAtCutoff:
    target: EvidenceJudgmentRef
    claim_id: ClaimId


@dataclass(frozen=True, slots=True)
class ClaimTargetNotYetEffective:
    target: EvidenceJudgmentRef


@dataclass(frozen=True, slots=True)
class ClaimNotYetEffective:
    target: EvidenceJudgmentRef
    claim_id: ClaimId


@dataclass(frozen=True, slots=True)
class ClaimNotCurrent:
    target: EvidenceJudgmentRef
    claim_id: ClaimId


@dataclass(frozen=True, slots=True)
class InvalidClaimReference:
    target: EvidenceJudgmentRef
    claim_id: ClaimId


@dataclass(frozen=True, slots=True)
class ContestedClaimHistory:
    target: EvidenceJudgmentRef
    reason: str


@dataclass(frozen=True, slots=True)
class InvalidClaimHistory:
    target: EvidenceJudgmentRef
    reason: str


@dataclass(frozen=True, slots=True)
class UnavailableClaimCatalog:
    target: EvidenceJudgmentRef
    reason: str


type ClaimMembershipFailure = (
    ClaimTargetNotKnownAtCutoff
    | ClaimNotKnownAtCutoff
    | ClaimTargetNotYetEffective
    | ClaimNotYetEffective
    | ClaimNotCurrent
    | InvalidClaimReference
    | ContestedClaimHistory
    | InvalidClaimHistory
)
type ClaimMembershipResolution = (
    ResolvedClaimMembership | ClaimMembershipFailure | UnavailableClaimCatalog
)


class ClaimCatalogMembershipResolver(Protocol):
    async def resolve(
        self,
        target: EvidenceJudgmentRef,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ClaimMembershipResolution: ...


class ClaimCatalogResolver:
    """Resolve target-owned claim membership without acquiring claim authority."""

    def __init__(self, store: ClaimCatalogStore) -> None:
        self._store = store

    async def resolve(
        self,
        target: EvidenceJudgmentRef,
        claim_id: ClaimId,
        *,
        effective_at: datetime,
        known_at: datetime,
    ) -> ClaimMembershipResolution:
        _validate_query(target, claim_id, effective_at, known_at)
        try:
            revisions = await self._store.load_claim_catalog(target)
        except ClaimCatalogReadUnavailable as error:
            return UnavailableClaimCatalog(target, str(error))
        return resolve_claim_membership(
            revisions,
            target,
            claim_id,
            effective_at=effective_at,
            known_at=known_at,
        )


def resolve_claim_membership(
    revisions: tuple[ClaimCatalogRevision, ...],
    target: EvidenceJudgmentRef,
    claim_id: ClaimId,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> ClaimMembershipResolution:
    _validate_query(target, claim_id, effective_at, known_at)
    if not revisions:
        return InvalidClaimReference(target, claim_id)

    known = tuple(
        revision for revision in revisions if revision.recorded_at <= known_at
    )
    if not known:
        return ClaimTargetNotKnownAtCutoff(target)
    try:
        validate_claim_catalog_history(known, target=target)
    except ContestedClaimCatalogHistory as error:
        return ContestedClaimHistory(target, str(error))
    except InvalidClaimCatalogHistory as error:
        return InvalidClaimHistory(target, str(error))

    active = tuple(
        revision for revision in known if revision.effective_at <= effective_at
    )
    if not active:
        return ClaimTargetNotYetEffective(target)
    selected = max(active, key=lambda revision: revision.version.value)
    if claim_id in selected.claim_ids:
        return ResolvedClaimMembership(target, claim_id, selected.version)

    # duplicate-code: this delegates an absent-member classification, while the
    # resolver above delegates a store result; sharing their call shapes would
    # couple distinct stages without centralizing any policy.
    # arid: disable
    result = _absent_claim_resolution(
        revisions,
        known,
        active,
        target,
        claim_id,
        effective_at=effective_at,
        known_at=known_at,
    )
    # arid: enable
    return result


def _validate_query(
    target: EvidenceJudgmentRef,
    claim_id: ClaimId,
    effective_at: datetime,
    known_at: datetime,
) -> None:
    if not is_evidence_judgment_ref(target):
        raise TypeError("target must be an EvidenceJudgmentRef")
    if type(claim_id) is not ClaimId:
        raise TypeError("claim_id must be ClaimId")
    _aware(effective_at, "effective_at")
    _aware(known_at, "known_at")


def _absent_claim_resolution(
    revisions: tuple[ClaimCatalogRevision, ...],
    known: tuple[ClaimCatalogRevision, ...],
    active: tuple[ClaimCatalogRevision, ...],
    target: EvidenceJudgmentRef,
    claim_id: ClaimId,
    *,
    effective_at: datetime,
    known_at: datetime,
) -> ClaimMembershipFailure:
    later_known = tuple(
        revision for revision in revisions if revision.recorded_at > known_at
    )
    if any(claim_id in revision.claim_ids for revision in later_known):
        return ClaimNotKnownAtCutoff(target, claim_id)
    if any(
        claim_id in revision.claim_ids and revision.effective_at > effective_at
        for revision in known
    ):
        return ClaimNotYetEffective(target, claim_id)
    if any(claim_id in revision.claim_ids for revision in active):
        return ClaimNotCurrent(target, claim_id)
    return InvalidClaimReference(target, claim_id)


# duplicate-code: application claim resolution owns ValueError semantics;
# sharing a domain validator would couple independent failure contracts.
# arid: disable
def _aware(value: object, field: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field} must be timezone-aware")


# arid: enable
